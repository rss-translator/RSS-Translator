import json
import httpx
from .base import TranslatorEngine
import logging
from time import sleep
from django.db import models
from django.utils.translation import gettext_lazy as _


class DeepLXTranslator(TranslatorEngine):
    # https://github.com/OwO-Network/DeepLX
    deeplx_api = models.CharField(
        max_length=255, default="http://127.0.0.1:1188/translate"
    )
    max_characters = models.IntegerField(default=5000)
    interval = models.IntegerField(_("Request Interval(s)"), default=3)
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

    class Meta:
        verbose_name = "DeepLX"
        verbose_name_plural = "DeepLX"

    def validate(self) -> bool:
        try:
            resp = self.translate("Hello World", "Chinese Simplified", validate=True)
            return resp.get("text") != ""
        except Exception:
            return False

    def translate(self, text: str, target_language: str, validate:bool=False, **kwargs) -> dict:
        logging.info(">>> DeepLX Translate [%s]: %s", target_language, text)
        target_code = self.language_code_map.get(target_language, None)
        translated_text = ""
        try:
            if target_code is None:
                logging.error(
                    "DeepLXTranslator->Not support target language:%s", target_language
                )

            data = {
                "text": text,
                "source_lang": "auto",
                "target_lang": target_code,
            }
            headers = {"Content-Type": "application/json"}
            post_data = json.dumps(data)
            resp = httpx.post(
                url=self.deeplx_api, headers=headers, data=post_data, timeout=10
            )
            if resp.status_code == 429:
                raise ("DeepLXTranslator-> IP has been blocked by DeepL temporarily")
            translated_text = resp.json()["data"]
        except Exception as e:
            logging.error("DeepLXTranslator->%s: %s", e, text)
        finally:
            if not validate:
                sleep(self.interval)
            return {"text": translated_text, "characters": len(text)}
