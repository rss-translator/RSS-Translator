# Translate the ../core/models.py file with sqlmodel transcription
import logging
import cityhash
from openai import OpenAI
from typing import Optional, List
from datetime import datetime
from uuid import uuid5, NAMESPACE_URL
from sqlmodel import Field, SQLModel, Relationship
from pydantic import field_validator
from ..config import settings as config
from abc import ABC, abstractmethod
from sqlalchemy.orm import with_polymorphic
from sqlalchemy import select
from sqlalchemy.orm import Session

class Engine(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, unique=True)
    valid: Optional[bool] = Field(default=None)
    is_ai: bool = Field(default=False)

    def translate(self, text: str, target_language: str, source_language: str = "auto", **kwargs) -> dict:
        pass

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
        pass

    def __str__(self):
        return self.name

class OpenAIInterface(Engine, table=True):
    is_ai: bool = Field(default=True)
    api_key: str = Field()
    base_url: str = Field(default="https://api.openai.com/v1")
    model: str = Field(default="gpt-3.5-turbo")
    translate_prompt: str = Field(default=config.default_title_translate_prompt)
    content_translate_prompt: str = Field(default=config.default_content_translate_prompt)
    temperature: float = Field(default=0.2)
    top_p: float = Field(default=0.2)
    frequency_penalty: float = Field(default=0)
    presence_penalty: float = Field(default=0)
    max_tokens: int = Field(default=2000)
    summary_prompt: str = Field(default=config.default_summary_prompt)

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
                fr = res.choices[0].finish_reason
                logging.info(">>> 翻译器验证：%s", fr)
                return True
            except Exception as e:
                logging.error("OpenAIInterface 验证 ->%s", e)
                return False

    def translate(self, text: str, target_language: str, system_prompt: str = None, user_prompt: str = None, text_type: str = "title", **kwargs) -> dict:
        logging.info(">>> 翻译 [%s]: %s", target_language, text)
        tokens = 0
        translated_text = ""
        system_prompt = system_prompt or (self.translate_prompt if text_type == "title" else self.content_translate_prompt)
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
            if res.choices and res.choices[0].message.content:
                translated_text = res.choices[0].message.content
                logging.info("OpenAITranslator->%s: %s", res.choices[0].finish_reason, translated_text)
            tokens = res.usage.total_tokens if res.usage else 0
        except Exception as e:
            logging.error("OpenAIInterface->%s: %s", e, text)

        return {"text": translated_text, "tokens": tokens}

    def summarize(self, text: str, target_language: str) -> dict:
        logging.info(">>> 总结 [%s]: %s", target_language, text)
        return self.translate(text, target_language, system_prompt=self.summary_prompt)

PolymorphicEngine = with_polymorphic(Engine, [OpenAIInterface])  # 添加其他 Engine 子类


class OFeed(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sid: str = Field(unique=True, index=True)
    name: Optional[str] = Field(default=None)
    feed_url: str = Field(unique=True)
    last_updated: Optional[datetime] = Field(default=None)
    last_pull: Optional[datetime] = Field(default=None)
    translation_display: int = Field(default=0)
    etag: str = Field(default="")
    size: int = Field(default=0)
    valid: Optional[bool] = Field(default=None)
    update_frequency: int = Field(default=30)
    max_posts: int = Field(default=20)
    quality: bool = Field(default=False)
    fetch_article: bool = Field(default=False)
    summary_detail: Optional[float] = Field(default=None)
    additional_prompt: Optional[str] = Field(default=None)
    category: Optional[str] = Field(default=None)

    t_feeds: List["TFeed"] = Relationship(back_populates="o_feed")

    translator_id: Optional[int] = Field(default=None, foreign_key="engine.id")
    summary_engine_id: Optional[int] = Field(default=None, foreign_key="engine.id")

    def translator(self, session: Session):
        return self.get_engine(self.translator_id, session)

    def summary_engine(self, session: Session):
        return self.get_engine(self.summary_engine_id, session)

    def get_engine(self, id: int, session: Session):
        if id:
            return session.execute(
                select(PolymorphicEngine).where(PolymorphicEngine.id == id)
            ).scalar_one_or_none()
        return None

    @field_validator("sid", mode="before")
    def set_sid(cls, v, info):
        if not v:
            return uuid5(NAMESPACE_URL, f"{info.data['feed_url']}:{config.secret_key}").hex
        return v


class TFeed(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sid: str = Field(unique=True, index=True)
    language: str
    status: Optional[bool] = Field(default=None)
    translate_title: bool = Field(default=False)
    translate_content: bool = Field(default=False)
    summary: bool = Field(default=False)
    total_tokens: int = Field(default=0)
    total_characters: int = Field(default=0)
    modified: Optional[datetime] = Field(default=None)
    size: int = Field(default=0)

    o_feed_id: Optional[int] = Field(default=None, foreign_key="ofeed.id")
    o_feed: Optional[OFeed] = Relationship(back_populates="t_feeds")

    @field_validator("sid", mode="before")
    def set_sid(cls, v, info, **kwargs):
        if not v:
            o_feed = kwargs.get("o_feed")
            if o_feed:
                return f"{o_feed.sid}_{info.data['language'].lower().replace('[^a-z]', '_')}"
        return v

class TranslatedContent(SQLModel, table=True):
    hash: str = Field(max_length=39, primary_key=True)
    original_content: str = Field()
    translated_language: str = Field(max_length=255)
    translated_content: str = Field()
    tokens: int = Field(default=0)
    characters: int = Field(default=0)

    def __str__(self):
        return self.original_content

    @classmethod
    def is_translated(cls, text: str, target_language: str):
        text_hash = str(cityhash.CityHash128(f"{text}{target_language}"))
        try:
            content = TranslatedContent.get(hash=text_hash)
            return {
                "text": content.translated_content,
                "tokens": content.tokens,
                "characters": content.characters,
            }
        except:
            logging.info("不存在于缓存中：%s", text)
            return None

    def save(self, *args, **kwargs):
        if not self.hash:
            self.hash = str(cityhash.CityHash128(f"{self.original_content}{self.translated_language}"))
        super().save(*args, **kwargs)