from .base import TranslatorEngine
import logging
from django.db import models
from time import sleep
from django.utils.translation import gettext_lazy as _


class TestTranslator(TranslatorEngine):
    translated_text = models.TextField(default="@@Translated Text@@")
    max_characters = models.IntegerField(default=50000)
    interval = models.IntegerField(_("Request Interval(s)"), default=3)
    is_ai = models.BooleanField(default=True, editable=False)

    class Meta:
        verbose_name = "Test"
        verbose_name_plural = "Test"

    def validate(self) -> bool:
        return True

    def translate(self, text:str, target_language:str, **kwargs) -> dict:
        logging.info(">>> Test Translate [%s]: %s", target_language, text)
        sleep(self.interval)
        return {'text': self.translated_text, "tokens": 0, "characters": len(text)}
    
    def summarize(self, text:str, target_language:str) -> dict:
        logging.info(">>> Test Summarize [%s]: %s", target_language, text)
        return self.translate(text, target_language)
