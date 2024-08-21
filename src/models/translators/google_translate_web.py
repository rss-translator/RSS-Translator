import logging
from time import sleep
from sqlalchemy import Integer
from sqlalchemy_utils import URLType
from sqlalchemy.orm import mapped_column
from src.models.core import Engine

class GoogleTranslateWeb(Engine):
    base_url = mapped_column(URLType, nullable=True, use_existing_column=True)
    max_characters = mapped_column(Integer, nullable=False, use_existing_column=True, default=5000)
    interval = mapped_column(Integer, nullable=False, use_existing_column=True, default=5)
    proxy = mapped_column(URLType, nullable=True, use_existing_column=True)
    language_code_map = {
        "English": "en",
        "Chinese Simplified": "zh-CN",
        "Chinese Traditional": "zh-TW",
        "Russian": "ru",
        "Japanese": "ja",
        "Korean": "ko",
        "Czech": "cs",
        "Danish": "da",
        "German": "de",
        "Spanish": "es",
        "French": "fr",
        "Indonesian": "id",
        "Italian": "it",
        "Hungarian": "hu",
        "Norwegian Bokmål": "no",
        "Dutch": "nl",
        "Polish": "pl",
        "Portuguese": "pt",
        "Swedish": "sv",
        "Turkish": "tr",
    }

    __mapper_args__ = {
        'polymorphic_identity': "Google Translate(Web)"
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        import translators as ts
        self.ts = ts

    def validate(self) -> bool:
        results = self.translate("hi", "Chinese Simplified", validate=True)
        return results.get("text") != ""

    def translate(self, text: str, target_language: str, validate:bool=False, **kwargs) -> dict:
        logging.info(">>> Google Translate Web Translate [%s]:", target_language)
        target_language = self.language_code_map.get(target_language)
        translated_text = ""
        if target_language is None:
            logging.error(
                "GoogleTranslateWeb->Not support target language:%s",
                target_language,
            )
            return {"text": translated_text, "characters": len(text)}
        try:
            results = self.ts.translate_text(text, to_language=target_language, translator="google", reset_host_url=self.base_url, proxies=self.proxy)
            if results:
                translated_text = results
        except Exception as e:
            logging.error("GoogleTranslateWeb->%s: %s", e, text)
        finally:
            if not validate:
                sleep(self.interval)

        return {"text": translated_text, "characters": len(text)}
