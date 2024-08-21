from .base import TranslatorEngine
import logging
from django.db import models
from django.utils.translation import gettext_lazy as _
from langdetect import detect

class FreeTranslators(TranslatorEngine):
    translators = models.TextField(null=True, blank=True, default="")  # list[dict]
    proxies = models.URLField(
        _("Proxy(optional)"),
        null=True,
        blank=True,
        default=None,
        help_text=("e.g. http://127.0.0.1:7890, https://127.0.0.1:1080"),
    )
    max_characters = models.IntegerField(default=5000)

    class Meta:
        verbose_name = "Free Translators"
        verbose_name_plural = "Free Translators"

    def _init(self):
        # if not self.translators:
        #     self.translators = []
        from easytranslator import EasyTranslator
        return EasyTranslator(translators=[])

    def validate(self) -> bool:
        return True

    def translate(self, text: str, target_language: str, source_language:str="auto", **kwargs) -> dict:
        et = self._init()
        try:
            source_language = detect(text) if source_language == "auto" else source_language
        except:
            source_language = "auto"
            logging.warning("Cannot detect source language:%s", text)
            
        results = et.translate(
            text=text, dest_lang=target_language, src_lang=source_language, proxies=self.proxies
        )
        
        translated_text = (
            results.get("translated_text") if results.get("status") == "success" else ""
        )
        return {"text": translated_text, "characters": len(text)}

    def translate_batch(self, text_list: list, target_language: str, **kwargs) -> dict:
        et = self._init()
        results = et.translate_batch(
            text_list=text_list, dest_lang=target_language, proxies=self.proxies
        )

        return results
        """
        {
            original_text: {
                "translated_text": "...",
                "status": "success" / "error"
                "error_info": error info if got error
            }
        }
        """
