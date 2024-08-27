import os
import uuid
import re
import logging
import cityhash
from sqlalchemy import Index, Column, Integer, String, Boolean, Text, DateTime, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base, Session
from sqlalchemy_utils import URLType

from openai import OpenAI
from rsstranslator.backend import settings

Base = declarative_base()

class Engine(Base):
    __tablename__ = 'engine'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    valid = Column(Boolean, nullable=True)
    is_ai = Column(Boolean, default=False)
    type = Column(String(50), nullable=False)
    
    __mapper_args__ = {
            'polymorphic_on': type,
            'polymorphic_identity': 'Engine'
        }

    def translate(self, text: str, target_language: str, source_language:str="auto", **kwargs) -> dict:
        raise NotImplementedError(
            "subclasses of Engine must provide a translate() method"
        )

    def min_size(self) -> int:
        if hasattr(self, "max_characters"):
            return int(self.max_characters * 0.7)
        if hasattr(self, "max_tokens"):
            return int(self.max_tokens * 0.7)
        return 0

    def max_size(self) -> int:
        if hasattr(self, "max_characters"):
            return int(self.max_characters * 0.9)
        if hasattr(self, "max_tokens"):
            return int(self.max_tokens * 0.9)
        return 0

    def validate(self) -> bool:
        raise NotImplementedError(
            "subclasses of Engine must provide a validate() method"
        )

class OpenAIInterface(Engine): 
    api_key = Column(String(255), nullable=True)
    base_url = Column(URLType, default="https://api.openai.com/v1", nullable=False)
    model = Column(String(100), default="Model Name",nullable=False)
    title_translate_prompt = Column(Text, nullable=False, default=settings.default_title_translate_prompt)
    content_translate_prompt = Column(Text, nullable=False, default=settings.default_content_translate_prompt)
    temperature = Column(Float, default=0.2, nullable=False)
    top_p = Column(Float, default=0.2, nullable=False)
    frequency_penalty = Column(Float, default=0, nullable=False)
    presence_penalty = Column(Float, default=0, nullable=False)
    max_tokens = Column(Integer, default=2000, nullable=False)
    summary_prompt = Column(Text, nullable=False, default=settings.default_summary_prompt)
    is_ai = True
    
    __mapper_args__ = {
        'polymorphic_identity': 'OpenAIInterface'
    }

    @property
    def client(self):
        return OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=120.0,
        )

    def validate(self) -> bool:
        if self.api_key:
            try:
                res = self.client.with_options(max_retries=3).chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": "Hi"}],
                    max_tokens=10,
                )
                fr = res.choices[
                    0
                ].finish_reason  # 有些第三方源在key或url错误的情况下，并不会抛出异常代码，而是返回html广告，因此添加该行。
                logging.info(">>> Translator Validate:%s", fr)
                return True
            except Exception as e:
                logging.error("OpenAIInterface validate ->%s", e)
        return False

    def translate(
        self,
        text: str,
        target_language: str,
        system_prompt: str = None,
        user_prompt: str = None,
        text_type: str = "title",
        **kwargs
    ) -> dict:
        logging.info(">>> Translate [%s]: %s", target_language, text)
        tokens = 0
        translated_text = ""
        system_prompt = (
            system_prompt or self.title_translate_prompt
            if text_type == "title"
            else self.content_translate_prompt
        )
        try:
            system_prompt = system_prompt.replace("{target_language}", target_language)
            if user_prompt:
                system_prompt += f"\n\n{user_prompt}"

            res = self.client.with_options(max_retries=3).chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "https://www.rsstranslator.com",
                    "X-Title": "RSS Translator"
                },
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                temperature=self.temperature,
                top_p=self.top_p,
                frequency_penalty=self.frequency_penalty,
                presence_penalty=self.presence_penalty,
                max_tokens=self.max_tokens,
            )
            #if res.choices[0].finish_reason.lower() == "stop" or res.choices[0].message.content:
            if res.choices and res.choices[0].message.content:
                translated_text = res.choices[0].message.content
                logging.info("OpenAITranslator->%s: %s", res.choices[0].finish_reason, translated_text)
            # else:
            #     translated_text = ''
            #     logging.warning("Translator->%s: %s", res.choices[0].finish_reason, text)
            tokens = res.usage.total_tokens if res.usage else 0
        except Exception as e:
            logging.error("OpenAIInterface->%s: %s", e, text)

        return {"text": translated_text, "tokens": tokens}

    def summarize(self, text: str, target_language: str) -> dict:
        logging.info(">>> Summarize [%s]: %s", target_language, text)
        return self.translate(text, target_language, system_prompt=self.summary_prompt)


class O_Feed(Base):
    __tablename__ = 'o_feed'
    
    id = Column(Integer, primary_key=True)
    sid = Column(String(255), unique=True, nullable=False)
    name = Column(String(100), nullable=True)
    feed_url = Column(URLType, unique=True, nullable=False)
    last_updated = Column(DateTime, nullable=True)
    last_pull = Column(DateTime, nullable=True)
    translation_display = Column(Integer, default=0)
    etag = Column(String(50), default="")
    size = Column(Integer, default=0)
    valid = Column(Boolean, nullable=True)
    update_frequency = Column(Integer, default=30)
    max_posts = Column(Integer, default=20)
    quality = Column(Boolean, default=False)
    fetch_article = Column(Boolean, default=False)
    
    summary_detail = Column(Float, default=0.0)
    additional_prompt = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)
    
    translator_id = Column(Integer, ForeignKey('engine.id'), nullable=True)
    translator = relationship("Engine", foreign_keys=[translator_id])
    summary_engine_id = Column(Integer, ForeignKey('engine.id'), nullable=True)
    summary_engine = relationship("Engine", foreign_keys=[summary_engine_id])
    
    t_feeds = relationship("T_Feed", back_populates="o_feed")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.sid:
            self.sid = uuid.uuid5(uuid.NAMESPACE_URL, f"{self.feed_url}:{os.getenv('SECRET_KEY')}").hex

    def get_translation_display(self):
        choices = {
            0: "Only Translation",
            1: "Translation | Original",
            2: "Original | Translation"
        }
        return choices.get(self.translation_display)

class T_Feed(Base):
    __tablename__ = 't_feed'
    
    id = Column(Integer, primary_key=True)
    sid = Column(String(255), unique=True, nullable=False)
    language = Column(String(50), nullable=False)
    o_feed_id = Column(Integer, ForeignKey('o_feed.id'), nullable=False)
    status = Column(Boolean, nullable=True)
    translate_title = Column(Boolean, default=False)
    translate_content = Column(Boolean, default=False)
    summary = Column(Boolean, default=False)
    total_tokens = Column(Integer, default=0)
    total_characters = Column(Integer, default=0)
    modified = Column(DateTime, nullable=True)
    size = Column(Integer, default=0)
    
    o_feed = relationship("O_Feed", back_populates="t_feeds")
    
    __table_args__ = (
        UniqueConstraint('o_feed_id', 'language', name='unique_o_feed_lang'),
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.sid:
            self.sid = f"{self.o_feed.sid}_{re.sub('[^a-z]', '_', self.language.lower())}"

class Translated_Content(Base):
    __tablename__ = 'translated_content'
    __table_args__ = (
        Index('idx_hash', 'hash'),
        Index('idx_translated_language', 'translated_language'),
    )

    hash = Column(String(50), primary_key=True)
    original_content = Column(Text)
    translated_language = Column(String(50))
    translated_content = Column(Text)
    tokens = Column(Integer, default=0)
    characters = Column(Integer, default=0)
    
    @classmethod
    def is_translated(cls, text:str, target_language:str, session: Session):
        text_hash = str(cityhash.CityHash128(f"{text}{target_language}"))
        content = session.query(cls).filter_by(hash=text_hash).first()
        # logging.info("Using cached translations:%s", text)
        if content:
            return {
                "text": content.translated_content,
                "tokens": content.tokens,
                "characters": content.characters,
            }
        logging.info("Does not exist in cache:%s", text)
        return None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.hash:
            self.hash = str(cityhash.CityHash128(f"{self.original_content}{self.translated_language}"))