import logging
from time import sleep

from sqlalchemy import Integer
from sqlalchemy_utils import URLType
from sqlalchemy.orm import mapped_column
from api.models.core import Engine

from PyDeepLX import PyDeepLX

class DeepLWeb(Engine):
    # https://github.com/OwO-Network/PyDeepLX
    max_characters = mapped_column(Integer, nullable=False, use_existing_column=True, default=5000)
    interval = mapped_column(Integer, nullable=False, use_existing_column=True, default=5)
    proxy = mapped_column(URLType, nullable=True, use_existing_column=True)
    language_code_map = {
        "English": "EN",
        "Chinese Simplified": "ZH",
        "Russian": "RU",
        "Japanese": "JA",
        "Korean": "KO",
        "Czech": "CS",
        "Danish": "DA",
        "German": "DE",
        "Spanish": "ES",
        "French": "FR",
        "Indonesian": "ID",
        "Italian": "IT",
        "Hungarian": "HU",
        "Norwegian Bokmål": "NB",
        "Dutch": "NL",
        "Polish": "PL",
        "Portuguese": "PT-PT",
        "Swedish": "SV",
        "Turkish": "TR",
    }

    __mapper_args__ = {
        'polymorphic_identity': 'DeepL Web'
    }

    def validate(self) -> bool:
        try:
            resp = self.translate("Hello World", "Chinese Simplified", validate=True)
            return resp.get("text") != ""
        except Exception as e:
            logging.error("DeepLWeb validate ->%s", e)
        return False

    def translate(self, text: str, target_language: str, validate:bool=False, **kwargs) -> dict:
        logging.info(">>> DeepL Web Translate [%s]: %s", target_language, text)
        target_code = self.language_code_map.get(target_language, None)
        translated_text = ""
        try:
            if target_code is None:
                raise Exception(
                    "DeepLWeb->Not support target language:%s",
                    target_language,
                )

            translated_text = PyDeepLX.translate(
                text=text, targetLang=target_code, sourceLang="auto", proxies=self.proxy
            )
        except Exception as e:
            logging.error("DeepLWeb->%s: %s", e, text)
        finally:
            if not validate:
                sleep(self.interval or 0)
        return {"text": translated_text, "characters": len(text)}
