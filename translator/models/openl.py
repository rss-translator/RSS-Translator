import uuid
import logging
import json
import httpx
from .base import TranslatorEngine
from django.utils.translation import gettext_lazy as _
from django.db import models
from encrypted_model_fields.fields import EncryptedCharField


class OpenlTranslator(TranslatorEngine):
    # https://docs.openl.club/
    api_key = EncryptedCharField(max_length=255)
    url = models.URLField(
        max_length=255, default="https://api.openl.club"
    )
    service_name = models.CharField(_("Translate Service Name"), max_length=50, default="deepl",help_text=_('Please get it from https://docs.openl.club/#/API/format?id=%e7%bf%bb%e8%af%91%e6%9c%8d%e5%8a%a1%e4%bb%a3%e7%a0%81%e5%90%8d'))
    max_characters = models.IntegerField(default=5000)
    language_code_map = {
        "English": "en",
        "Chinese Simplified": "zh",
        "Japanese": "ja",
        "Spanish": "es",
        "French": "fr",
        "Russian": "ru",
        "Italian": "it",
        "Spanish": "es",
        "Polish": "pl",
        "Portuguese": "pt",
    }

    class Meta:
        verbose_name = "Openl"
        verbose_name_plural = "Openl"

    def validate(self) -> bool:
        try:
            resp = httpx.post(
                url=self.url + "/user/info",
                headers={"content-type": "application/json"},
                data=json.dumps({"apikey": self.api_key}),
                timeout=10,
            )
            resp.raise_for_status()
            results = resp.json()
            return results.get("status") is True
        except Exception as e:
            logging.error("OpenlTranslator->%s", e)
            return False

    def translate(self, text: str, target_language: str, **kwargs) -> dict:
        logging.info(">>> Openl Translate [%s]: %s", target_language, text)
        target_code = self.language_code_map.get(target_language, None)
        translated_text = ""
        try:
            if target_code is None:
                logging.error(
                    "OpenlTranslator->Not support target language:%s", target_language
                )

            resp = httpx.post(
                url=self.url + f"/services/{self.service_name}/translate",
                headers={"content-type": "application/json"},
                data=json.dumps({"apikey": self.api_key, "text": text, "target_lang": target_code}),
                timeout=10,
            )
            resp.raise_for_status()
            results = resp.json()
            translated_text = results.get("result") if results.get("status") is True else ""
        except Exception as e:
            logging.error("OpenlTranslator->%s: %s", e, text)
        finally:
            return {"text": translated_text, "characters": len(text)}
