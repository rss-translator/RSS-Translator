import uuid
import json
import httpx
import logging
from sqlalchemy import Integer, String
from sqlalchemy_utils import URLType
from sqlalchemy.orm import mapped_column
from rsstranslator.backend.models.core import Engine

class CaiYun(Engine):

    api_key = mapped_column(String(255), nullable=False, use_existing_column=True)
    base_url = mapped_column(URLType, nullable=False, use_existing_column=True, default="http://api.interpreter.caiyunapi.com/v1/translator")
    max_characters = mapped_column(Integer, nullable=False, use_existing_column=True, default=5000)

    __mapper_args__ = {
        'polymorphic_identity': 'CaiYun'
    }

    language_code_map = {
        "English": "en",
        "Chinese Simplified": "zh",
        "Japanese": "ja",
        "Korean": "ko",
        "Spanish": "es",
        "French": "fr",
        "Russian": "ru",
    }

    def validate(self) -> bool:
        result = self.translate("Hi", "Chinese Simplified")
        return result.get("text") != ""

    def translate(self, text: str, target_language: str, **kwargs) -> dict:
        logging.info(">>> CaiYun Translate [%s]: %s", target_language, text)
        target_code = self.language_code_map.get(target_language, None)
        translated_text = ""
        try:
            if target_code is None:
                raise Exception(
                    "CaiYun->Not support target language:%s", target_language
                )

            payload = {
                "source": text,
                "trans_type": f"auto2{target_code}",
                "request_id": uuid.uuid4().hex,
                "detect": True,
            }

            headers = {
                "content-type": "application/json",
                "x-authorization": f"token {self.api_key}",
            }

            resp = httpx.post(
                url=self.base_url, headers=headers, data=json.dumps(payload), timeout=10
            )
            resp.raise_for_status()
            translated_text = resp.json()["target"]
        except Exception as e:
            logging.error("CaiYun->%s: %s", e, text)
        finally:
            return {"text": translated_text, "characters": len(text)}
