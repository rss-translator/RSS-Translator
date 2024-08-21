from time import sleep
from .base import TranslatorEngine
import logging
from django.db import models
from django.utils.translation import gettext_lazy as _

class GoogleTranslateWebTranslator(TranslatorEngine):
    base_url = models.URLField(
        _("URL"), null=True, blank=True, help_text=_("It is recommended to leave this blank in order to automatically select the best server")
    ) # https://translate.googleapis.com/translate_a/single
    proxy = models.URLField(_("Proxy(optional)"), null=True, blank=True, default=None)
    interval = models.IntegerField(_("Request Interval(s)"), default=1)
    max_characters = models.IntegerField(default=1000)
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

    class Meta:
        verbose_name = "Google Translate(Web)"
        verbose_name_plural = "Google Translate(Web)"

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
                "GoogleTranslateWebTranslator->Not support target language:%s",
                target_language,
            )
            return {"text": translated_text, "characters": len(text)}
        try:
            # params = {
            #     "client": "gtx",
            #     "sl": "auto",
            #     "tl": target_language,
            #     "dt": "t",
            #     "q": text,
            # }
            # resp = httpx.get(self.base_url, params=params, timeout=10, proxy=self.proxy)
            # resp.raise_for_status()
            # resp_json = resp.json()
            results = self.ts.translate_text(text, to_language=target_language, translator="google", reset_host_url=self.base_url, proxies=self.proxy)
            if results:
                translated_text = results
        except Exception as e:
            logging.error("GoogleTranslateWebTranslator->%s: %s", e, text)
        finally:
            if not validate:
                sleep(self.interval)
            return {"text": translated_text, "characters": len(text)}
