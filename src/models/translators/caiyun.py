import uuid
import json
import httpx
import logging
from sqlalchemy import Column, Integer, String
from sqlalchemy_utils import URLType
from src.models.core import Engine

class CaiYun(Engine):
    
    token = Column(String(255))
    base_url = Column(URLType, default="http://api.interpreter.caiyunapi.com/v1/translator")
    max_characters = Column(Integer, default=5000)

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
                raise(
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
                "x-authorization": f"token {self.token}",
            }

            resp = httpx.post(
                url=self.url, headers=headers, data=json.dumps(payload), timeout=10
            )
            resp.raise_for_status()
            translated_text = resp.json()["target"]
        except Exception as e:
            logging.error("CaiYun->%s: %s", e, text)
        finally:
            return {"text": translated_text, "characters": len(text)}
