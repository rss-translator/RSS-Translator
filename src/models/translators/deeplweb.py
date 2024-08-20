from PyDeepLX import PyDeepLX
from .base import TranslatorEngine
import logging
from time import sleep
from django.db import models
from django.utils.translation import gettext_lazy as _


class DeepLWebTranslator(TranslatorEngine):
    # https://github.com/OwO-Network/PyDeepLX
    max_characters = models.IntegerField(default=5000)
    interval = models.IntegerField(_("Request Interval(s)"), default=5)
    proxy = models.URLField(_("Proxy(optional)"), null=True, blank=True, default=None)
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
        verbose_name = "DeepL Web"
        verbose_name_plural = "DeepL Web"

    def validate(self) -> bool:
        try:
            resp = self.translate("Hello World", "Chinese Simplified", validate=True)
            return resp.get("text") != ""
        except Exception as e:
            logging.error("DeepLWebTranslator validate ->%s", e)
            return False

    def translate(self, text: str, target_language: str, validate:bool=False, **kwargs) -> dict:
        logging.info(">>> DeepL Web Translate [%s]: %s", target_language, text)
        target_code = self.language_code_map.get(target_language, None)
        translated_text = ""
        try:
            if target_code is None:
                logging.error(
                    "DeepLWebTranslator->Not support target language:%s",
                    target_language,
                )

            translated_text = PyDeepLX.translate(
                text=text, targetLang=target_code, sourceLang="auto", proxies=self.proxy
            )
        except Exception as e:
            logging.error("DeepLWebTranslator->%s: %s", e, text)
        finally:
            if not validate:
                sleep(self.interval)
            return {"text": translated_text, "characters": len(text)}
