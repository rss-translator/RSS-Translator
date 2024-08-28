import os
import uuid
import re
import logging
import cityhash
from datetime import datetime
from sqlalchemy import (
    Index,
    Integer,
    String,
    Boolean,
    Text,
    DateTime,
    Float,
    ForeignKey,
    UniqueConstraint,
    select
)
from sqlalchemy.orm import relationship, DeclarativeBase, Session, Mapped, mapped_column
from sqlalchemy_utils import URLType

from openai import OpenAI
from rsstranslator.backend import settings
from typing import Optional, List


class Base(DeclarativeBase):
    pass


class Engine(Base):
    __tablename__ = "engine"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    is_available: Mapped[bool] = mapped_column(nullable=True)
    is_ai: Mapped[bool] = mapped_column(nullable=False, default=False)
    translated_feeds: Mapped[List["O_Feed"]] = relationship(
        back_populates="translator", foreign_keys="[O_Feed.translator_id]"
    )
    summarized_feeds: Mapped[List["O_Feed"]] = relationship(
        back_populates="summary_engine", foreign_keys="[O_Feed.summary_engine_id]"
    )
    caches: Mapped[List["Cache"]] = relationship(
        back_populates="engine"
    )

    type: Mapped[str] = mapped_column(nullable=False)

    __mapper_args__ = {"polymorphic_on": type, "polymorphic_identity": "Engine"}

    def translate(
        self, text: str, target_language: str, source_language: str = "auto", **kwargs
    ) -> dict:
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
    api_key: Mapped[str] = mapped_column(String(255), default="API KEY")
    base_url: Mapped[URLType] = mapped_column(
        URLType, default="https://api.openai.com/v1"
    )
    model: Mapped[str] = mapped_column(String(100), default="Model Name")
    title_translate_prompt: Mapped[str] = mapped_column(
        Text, default=settings.default_title_translate_prompt
    )
    content_translate_prompt: Mapped[str] = mapped_column(
        Text, default=settings.default_content_translate_prompt
    )
    temperature: Mapped[float] = mapped_column(default=0.2)
    top_p: Mapped[float] = mapped_column(default=0.2)
    frequency_penalty: Mapped[float] = mapped_column(default=0)
    presence_penalty: Mapped[float] = mapped_column(default=0)
    max_tokens: Mapped[int] = mapped_column(default=2000)
    summary_prompt: Mapped[str] = mapped_column(
        Text, default=settings.default_summary_prompt
    )
    is_ai = True

    __mapper_args__ = {"polymorphic_identity": "OpenAIInterface"}

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
        **kwargs,
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
                    "X-Title": "RSS Translator",
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
            # if res.choices[0].finish_reason.lower() == "stop" or res.choices[0].message.content:
            if res.choices and res.choices[0].message.content:
                translated_text = res.choices[0].message.content
                logging.info(
                    "OpenAITranslator->%s: %s",
                    res.choices[0].finish_reason,
                    translated_text,
                )
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


class Category(Base):
    __tablename__ = "category"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    feeds: Mapped[List["O_Feed"]] = relationship(back_populates="category")


class O_Feed(Base):
    __tablename__ = "o_feed"

    id: Mapped[int] = mapped_column(primary_key=True)
    # sid: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=True)
    feed_url: Mapped[str] = mapped_column(unique=True, nullable=False)
    last_updated: Mapped[datetime] = mapped_column(nullable=True)
    last_pull: Mapped[datetime] = mapped_column(nullable=True)
    translation_display: Mapped[int] = mapped_column(Integer, default=0)
    etag: Mapped[str] = mapped_column(String(50), default="")
    size: Mapped[int] = mapped_column(default=0)
    valid: Mapped[bool] = mapped_column(nullable=True)
    update_frequency: Mapped[int] = mapped_column(default=30)
    max_posts: Mapped[int] = mapped_column(default=20)
    quality: Mapped[bool] = mapped_column(default=False)
    fetch_article: Mapped[bool] = mapped_column(default=False)

    summary_detail: Mapped[float] = mapped_column(default=0.0)
    additional_prompt: Mapped[str] = mapped_column(Text, nullable=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("category.id"), nullable=True)
    category: Mapped["Category"] = relationship(back_populates="feeds")

    translator_id: Mapped[int] = mapped_column(ForeignKey("engine.id"), nullable=True)
    translator: Mapped["Engine"] = relationship(
        back_populates="translated_feeds", foreign_keys=translator_id
    )

    summary_engine_id: Mapped[int] = mapped_column(
        ForeignKey("engine.id"), nullable=True
    )
    summary_engine: Mapped["Engine"] = relationship(
        back_populates="summarized_feeds", foreign_keys=summary_engine_id
    )

    t_feeds: Mapped[List["T_Feed"]] = relationship(back_populates="o_feed")

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     if not self.sid:
    #         self.sid = uuid.uuid5(uuid.NAMESPACE_URL, f"{self.feed_url}:{os.getenv('SECRET_KEY')}").hex

    def get_translation_display(self):
        choices = {
            0: "Only Translation",
            1: "Translation | Original",
            2: "Original | Translation",
        }
        return choices.get(self.translation_display)


class T_Feed(Base):
    __tablename__ = "t_feed"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # sid = mapped_column(String(255), unique=True, nullable=False)
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    o_feed_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("o_feed.id"), nullable=False
    )
    status: Mapped[bool] = mapped_column(Boolean, nullable=True)
    translate_title: Mapped[bool] = mapped_column(Boolean, default=False)
    translate_content: Mapped[bool] = mapped_column(Boolean, default=False)
    summary: Mapped[bool] = mapped_column(Boolean, default=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_characters: Mapped[int] = mapped_column(Integer, default=0)
    modified: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    size: Mapped[int] = mapped_column(Integer, default=0)

    o_feed_id: Mapped[int] = mapped_column(ForeignKey("o_feed.id"), nullable=True)
    o_feed: Mapped["O_Feed"] = relationship("O_Feed", back_populates="t_feeds")

    __table_args__ = (
        UniqueConstraint("o_feed_id", "language", name="unique_o_feed_lang"),
    )

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     if not self.sid:
    #         self.sid = f"{self.o_feed.sid}_{re.sub('[^a-z]', '_', self.language.lower())}"


class Cache(Base):
    __tablename__ = "cache"

    type: Mapped[str] = mapped_column(nullable=False)
    __mapper_args__ = {"polymorphic_on": type, "polymorphic_identity": "Cache"}

    hash: Mapped[str] = mapped_column(String(50), primary_key=True)
    original_content: Mapped[str] = mapped_column(Text)
    target_language: Mapped[str] = mapped_column(String(50))
    target_content: Mapped[str] = mapped_column(Text)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    characters: Mapped[int] = mapped_column(Integer, default=0)

    engine_id: Mapped[int] = mapped_column(ForeignKey("engine.id"))
    engine = relationship("Engine", back_populates="caches")

    @staticmethod
    def generate_hash(text: str, language: str) -> str:
        return str(cityhash.CityHash128(f"{text}{language}"))

    @classmethod
    def is_translated(cls, text: str, target_language: str, session: Session):
        text_hash = cls.generate_hash(text, target_language)
        content = session.execute(
            select(cls).filter_by(hash=text_hash)
        ).scalar_one_or_none()
        # logging.info("Using cached translations:%s", text)
        if content:
            return {
                "text": content.target_content,
                "tokens": content.tokens,
                "characters": content.characters,
            }
        logging.info("Does not exist in cache:%s", text)
        return None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.hash:
            self.hash = self.generate_hash(self.original_content, self.target_language)

class TranslationCache(Cache):
    __mapper_args__ = {"polymorphic_identity": "Translation Cache"}

class SummaryCache(Cache):
    __mapper_args__ = {"polymorphic_identity": "Summary Cache"}