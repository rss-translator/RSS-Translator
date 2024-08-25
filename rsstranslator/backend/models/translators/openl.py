import logging
import json
import httpx

from sqlalchemy import Column, Integer, String
from sqlalchemy_utils import URLType
from sqlalchemy.orm import mapped_column
from rsstranslator.backend.models.core import Engine


class Openl(Engine):
    # https://docs.openl.club/
    api_key = mapped_column(String(255),nullable=False,use_existing_column=True)  
    base_url = mapped_column(URLType,nullable=False,use_existing_column=True, default="https://api.openl.club")
    service_name = Column(String(100), nullable=False, default="deepl")
    max_characters = mapped_column(Integer, nullable=False, use_existing_column=True, default=5000)
    language_code_map = {
        "English": "en",
        "Chinese Simplified": "zh",
        "Japanese": "ja",
        "Spanish": "es",
        "French": "fr",
        "Russian": "ru",
        "Italian": "it",
        "Polish": "pl",
        "Portuguese": "pt",
    }

    __mapper_args__ = {
        'polymorphic_identity': 'Openl'
    }

    def validate(self) -> bool:
        try:
            resp = httpx.post(
                url=self.base_url + "/user/info",
                headers={"content-type": "application/json"},
                data=json.dumps({"apikey": self.api_key}),
                timeout=10,
            )
            resp.raise_for_status()
            results = resp.json()
            return results.get("status") is True
        except Exception as e:
            logging.error("Openl->%s", e)

        return False

    def translate(self, text: str, target_language: str, **kwargs) -> dict:
        logging.info(">>> Openl Translate [%s]: %s", target_language, text)
        target_code = self.language_code_map.get(target_language, None)
        translated_text = ""
        try:
            if target_code is None:
                raise Exception(
                    "Openl->Not support target language:%s", target_language
                )

            resp = httpx.post(
                url=self.base_url + f"/services/{self.service_name}/translate",
                headers={"content-type": "application/json"},
                data=json.dumps({"apikey": self.api_key, "text": text, "target_lang": target_code}),
                timeout=10,
            )
            resp.raise_for_status()
            results = resp.json()
            translated_text = results.get("result") if results.get("status") is True else ""
        except Exception as e:
            logging.error("Openl->%s: %s", e, text)
    
        return {"text": translated_text, "characters": len(text)}
