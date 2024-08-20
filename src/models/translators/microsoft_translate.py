import httpx
from .base import TranslatorEngine
import logging
from django.db import models
from encrypted_model_fields.fields import EncryptedCharField
from django.utils.translation import gettext_lazy as _
import uuid


class MicrosoftTranslator(TranslatorEngine):
    # https://learn.microsoft.com/en-us/azure/ai-services/translator/language-support
    api_key = EncryptedCharField(_("API Key"), max_length=255)
    location = models.CharField(max_length=100)
    endpoint = models.CharField(
        max_length=255, default="https://api.cognitive.microsofttranslator.com"
    )
    max_characters = models.IntegerField(default=5000)
    language_code_map = {
        "English": "en",
        "Chinese Simplified": "zh-Hans",
        "Chinese Traditional": "zh-Hant",
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
        "Norwegian Bokmål": "nb",
        "Dutch": "nl",
        "Polish": "pl",
        "Portuguese": "pt-pt",
        "Swedish": "sv",
        "Turkish": "tr",
    }

    class Meta:
        verbose_name = "Microsoft Translator"
        verbose_name_plural = "Microsoft Translator"

    def validate(self) -> bool:
        result = self.translate("Hi", "Chinese Simplified")
        return result.get("text") != ""

    def translate(self, text: str, target_language: str, **kwargs) -> dict:
        logging.info(">>> Microsoft Translate [%s]: %s", target_language, text)
        target_code = self.language_code_map.get(target_language, None)
        translated_text = ""
        try:
            if target_code is None:
                logging.error(
                    "MicrosoftTranslator->Not support target language:%s",
                    target_language,
                )

            constructed_url = f"{self.endpoint}/translate"
            params = {"api-version": "3.0", "to": target_code}
            headers = {
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Ocp-Apim-Subscription-Region": self.location,
                "Content-type": "application/json",
                "X-ClientTraceId": str(uuid.uuid4()),
            }
            body = [{"text": text}]

            with httpx.Client() as client:
                resp = client.post(
                    constructed_url,
                    params=params,
                    headers=headers,
                    json=body,
                    timeout=10,
                )
                resp.raise_for_status()
                translated_text = resp.json()[0]["translations"][0]["text"]
            # [{'detectedLanguage': {'language': 'en', 'score': 1.0}, 'translations': [{'text': '你好，我叫约翰。', 'to': 'zh-Hans'}]}]
        except Exception as e:
            logging.error("MicrosoftTranslator->%s: %s", e, text)
        finally:
            return {"text": translated_text, "characters": len(text)}
