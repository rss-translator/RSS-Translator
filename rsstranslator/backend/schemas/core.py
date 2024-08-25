from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime

class EngineBase(BaseModel):
    name: str
    valid: Optional[bool] = None
    is_ai: bool = False
    type: str

class EngineCreate(EngineBase):
    pass

class Engine(EngineBase):
    id: int

    class ConfigDict:
        from_attributes = True

class OpenAIInterfaceBase(EngineBase):
    api_key: str
    base_url: HttpUrl = Field(default="https://api.openai.com/v1")
    model: str = Field(default="Model Name")
    title_translate_prompt: str
    content_translate_prompt: str
    temperature: float = 0.2
    top_p: float = 0.2
    frequency_penalty: float = 0
    presence_penalty: float = 0
    max_tokens: int = 2000
    summary_prompt: str
    is_ai: bool = True

class OpenAIInterfaceCreate(OpenAIInterfaceBase):
    pass

class OpenAIInterface(OpenAIInterfaceBase):
    id: int

    class ConfigDict:
        from_attributes = True

class OFeedBase(BaseModel):
    name: Optional[str] = None
    feed_url: HttpUrl
    translation_display: int = 0
    etag: str = ""
    size: int = 0
    valid: Optional[bool] = None
    update_frequency: int = 30
    max_posts: int = 20
    quality: bool = False
    fetch_article: bool = False
    summary_detail: float = 0.0
    additional_prompt: Optional[str] = None
    category: Optional[str] = None

class OFeedCreate(OFeedBase):
    pass

class OFeed(OFeedBase):
    id: int
    sid: str
    last_updated: Optional[datetime] = None
    last_pull: Optional[datetime] = None
    translator_id: Optional[int] = None
    summary_engine_id: Optional[int] = None

    class ConfigDict:
        from_attributes = True

class TFeedBase(BaseModel):
    language: str
    status: Optional[bool] = None
    translate_title: bool = False
    translate_content: bool = False
    summary: bool = False
    total_tokens: int = 0
    total_characters: int = 0
    size: int = 0

class TFeedCreate(TFeedBase):
    o_feed_id: int

class TFeed(TFeedBase):
    id: int
    sid: str
    o_feed_id: int
    modified: Optional[datetime] = None

    class ConfigDict:
        from_attributes = True

class TranslatedContentBase(BaseModel):
    original_content: str
    translated_language: str
    translated_content: str
    tokens: int = 0
    characters: int = 0

class TranslatedContentCreate(TranslatedContentBase):
    pass

class TranslatedContent(TranslatedContentBase):
    hash: str

    class ConfigDict:
        from_attributes = True
