import logging
from sqlalchemy import Column, Integer, String
from sqlalchemy_utils import URLType
from src.models.core import Engine

import deepl

class DeepL(Engine):
    # https://github.com/DeepLcom/deepl-python
    api_key = Column(String(255))
    max_characters = Column(Integer, default=5000)
    server_url = Column(URLType, nullable=True)
    proxy = Column(URLType, nullable=True)
    language_code_map = {
        "English": "EN-US",
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
        'polymorphic_identity': 'DeepL'
    }

    @property
    def client(self):
        return deepl.Translator(
            self.api_key, server_url=self.server_url, proxy=self.proxy
        )

    def validate(self) -> bool:
        try:
            usage = self.client.get_usage()
            return usage.character.valid
        except Exception as e:
            logging.error("DeepL validate ->%s", e)
            return False

    def translate(self, text: str, target_language: str, source_language:str="auto", **kwargs) -> dict:
        logging.info(">>> DeepL Translate [%s]: %s", target_language, text)
        target_code = self.language_code_map.get(target_language, None)
        translated_text = ""
        try:
            if target_code is None:
                logging.error(
                    "DeepL->Not support target language:%s", target_language
                )
            resp = self.client.translate_text(
                text,
                target_lang=target_code,
                preserve_formatting=True,
                split_sentences="nonewlines",
            )
            translated_text = resp.text
        except Exception as e:
            logging.error("DeepL->%s: %s", e, text)
        return {"text": translated_text, "characters": len(text)}
