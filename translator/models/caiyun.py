import uuid
import json
import httpx
from .base import TranslatorEngine
import logging
from django.db import models
from encrypted_model_fields.fields import EncryptedCharField


class CaiYunTranslator(TranslatorEngine):
    # https://docs.caiyunapp.com/blog/2018/09/03/lingocloud-api/
    token = EncryptedCharField(max_length=255)
    url = models.URLField(
        max_length=255, default="http://api.interpreter.caiyunai.com/v1/translator"
    )
    max_characters = models.IntegerField(default=5000)
    language_code_map = {
        "English": "en",
        "Chinese Simplified": "zh",
        "Japanese": "ja",
        "Korean": "ko",
        "Spanish": "es",
        "French": "fr",
        "Russian": "ru",
    }

    class Meta:
        verbose_name = "CaiYun"
        verbose_name_plural = "CaiYun"

    def validate(self) -> bool:
        result = self.translate("Hi", "Chinese Simplified")
        return result.get("text") != ""

    def translate(self, text: str, target_language: str, **kwargs) -> dict:
        logging.info(">>> CaiYun Translate [%s]: %s", target_language, text)
        target_code = self.language_code_map.get(target_language, None)
        translated_text = ""
        try:
            if target_code is None:
                logging.error(
                    "CaiYunTranslator->Not support target language:%s", target_language
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
            logging.error("CaiYunTranslator->%s: %s", e, text)
        finally:
            return {"text": translated_text, "characters": len(text)}
