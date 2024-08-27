from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from enum import Enum
from pydantic import ConfigDict

class TranslationServiceType(str, Enum):
    GOOGLE = "google"
    BAIDU = "baidu"
    YOUDAO = "youdao"
    # ... 其他翻译服务

class Feed(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str
    translation_model: str | None
    translation_id: int | None
    # model_config = ConfigDict(arbitrary_types_allowed=True)

class Translation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    feed_id: int = Field(foreign_key="feed.id")
    #feed: Feed = Relationship(back_populates="translation")
    type: TranslationServiceType
    model_config = ConfigDict(arbitrary_types_allowed=True)


class GoogleTranslation(Translation, table=True):
    # id: Optional[int] = Field(default=None, primary_key=True)
    api_key: str
    source_lang: str
    target_lang: str
    # model_config = ConfigDict(arbitrary_types_allowed=True)


class BaiduTranslation(Translation, table=True):
    # id: Optional[int] = Field(default=None, primary_key=True)
    app_id: str
    app_key: str
    from_lang: str
    to_lang: str
    # model_config = ConfigDict(arbitrary_types_allowed=True)


# ... 其他翻译服务模型