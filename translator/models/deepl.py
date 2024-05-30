import deepl
from .base import TranslatorEngine
import logging
from django.db import models
from encrypted_model_fields.fields import EncryptedCharField
from django.utils.translation import gettext_lazy as _


class DeepLTranslator(TranslatorEngine):
    # https://github.com/DeepLcom/deepl-python
    api_key = EncryptedCharField(_("API Key"), max_length=255)
    max_characters = models.IntegerField(default=5000)
    server_url = models.URLField(_("API URL(optional)"), null=True, blank=True)
    proxy = models.URLField(_("Proxy(optional)"), null=True, blank=True)
    language_code_map = {
        "English": "EN-US",
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
        verbose_name = "DeepL"
        verbose_name_plural = "DeepL"

    def _init(self):
        return deepl.Translator(
            self.api_key, server_url=self.server_url, proxy=self.proxy
        )

    def validate(self) -> bool:
        try:
            translator = self._init()
            usage = translator.get_usage()
            return usage.character.valid
        except Exception as e:
            logging.error("DeepLTranslator validate ->%s", e)
            return False

    def translate(self, text: str, target_language: str, **kwargs) -> dict:
        logging.info(">>> DeepL Translate [%s]: %s", target_language, text)
        target_code = self.language_code_map.get(target_language, None)
        translated_text = ""
        try:
            if target_code is None:
                logging.error(
                    "DeepLTranslator->Not support target language:%s", target_language
                )
            translator = self._init()
            resp = translator.translate_text(
                text,
                target_lang=target_code,
                preserve_formatting=True,
                split_sentences="nonewlines",
            )
            translated_text = resp.text
        except Exception as e:
            logging.error("DeepLTranslator->%s: %s", e, text)
        return {"text": translated_text, "characters": len(text)}
