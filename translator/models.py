import logging
import uuid

import cityhash
import deepl
import httpx
from django.db import models
from encrypted_model_fields.fields import EncryptedCharField
from openai import OpenAI
from django.utils.translation import gettext_lazy as _



class Translated_Content(models.Model):
    hash = models.BinaryField(max_length=8, unique=True)
    original_content = models.TextField()

    translated_language = models.CharField(max_length=255)
    translated_content = models.TextField()

    tokens = models.IntegerField(default=0)
    characters = models.IntegerField(default=0)

    def __str__(self):
        return self.original_content


class TranslatorEngine(models.Model):
    name = models.CharField(_("Name"), max_length=100, unique=True)
    valid = models.BooleanField(_("Valid"),null=True)

    def translate(self, text: str, target_language) -> dict:
        raise NotImplementedError(
            "subclasses of TranslatorEngine must provide a translate() method"
        )

    def validate(self) -> bool:
        raise NotImplementedError(
            "subclasses of TranslatorEngine must provide a validate() method"
        )

    @classmethod
    def is_translated(cls, text, target_language):
        text_hash = cityhash.CityHash64(f"{text}{target_language}").to_bytes(8, byteorder='little')
        try:
            content = Translated_Content.objects.get(hash=text_hash)
            # logging.debug("Using cached translations:%s", text)
            return {
                'result': content.translated_content,
                'tokens': content.tokens,
                'characters': content.characters
            }
        except Translated_Content.DoesNotExist:
            logging.debug("Does not exist in cache:%s", text)
            return None

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class OpenAITranslator(TranslatorEngine):
    # https://platform.openai.com/docs/api-reference/chat
    api_key = EncryptedCharField(max_length=255)
    model = models.CharField(max_length=100, default="gpt-3.5-turbo")
    prompt = models.TextField(default="Translate the following to {target_language},only returns translations.\n{text}")
    temperature = models.FloatField(default=0.5)
    max_tokens = models.IntegerField(default=1000)

    class Meta:
        verbose_name = "OpenAI"
        verbose_name_plural = "OpenAI"

    def validate(self):
        if self.api_key:
            try:
                openai = OpenAI(
                    api_key=self.api_key,
                )
                res = openai.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": 'Hi'}],
                    temperature=self.temperature,
                    max_tokens=10,
                )
                return True
            except Exception as e:
                return False

    def translate(self, text, target_language):
        logging.debug(">>> OpenAI Translate [%s]:", target_language)
        openai = OpenAI(
            api_key=self.api_key,
        )
        tokens = 0
        translated_text = ""
        try:
            prompt = self.prompt.format(target_language=target_language, text=text)
            res = openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            translated_text = res.choices[0].message.content
            tokens = res.usage.total_tokens
        except Exception as e:
            logging.error("OpenAITranslator->{text}: {e}")

        return {'result': translated_text, "tokens": tokens, "characters": len(text)}


class DeepLTranslator(TranslatorEngine):
    # https://github.com/DeepLcom/deepl-python
    api_key = EncryptedCharField(max_length=255)
    # url = models.CharField(max_length=255, default="https://api-free.deepl.com/v2/translate")
    language_code_map = {
        "English": "EN-US",
        "Chinese Simplified": "ZH",
        "Chinese Traditional": None,
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

    def validate(self) -> bool:
        try:
            translator = deepl.Translator(self.api_key)
            usage = translator.get_usage()
            return usage.character.valid
        except Exception as e:
            return False

    def translate(self, text, target_language):
        logging.debug(">>> DeepL Translate [%s]: %s", target_language, text)
        target_code = self.language_code_map.get(target_language, None)
        try:
            if target_code is None:
                logging.error("DeepLTranslator->%s: Not support target language", text)
            translator = deepl.Translator(self.api_key)
            resp = translator.translate_text(text, target_lang=target_code)
            translated_text = resp.text
        except Exception as e:
            logging.error("DeepLTranslator->%s: %s", text, e)
        return {'result': translated_text, "characters": len(text)}


class MicrosoftTranslator(TranslatorEngine):
    # https://learn.microsoft.com/en-us/azure/ai-services/translator/language-support
    api_key = EncryptedCharField(max_length=255)
    location = models.CharField(max_length=100)
    endpoint = models.CharField(max_length=255, default="https://api.cognitive.microsofttranslator.com")
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
        return result.get("result") != ""

    def translate(self, text, target_language) -> dict:
        logging.debug(">>> Microsoft Translate [%s]: %s", target_language, text)
        target_code = self.language_code_map.get(target_language, None)
        translated_text = ""
        try:
            if target_code is None:
                logging.error("MicrosoftTranslator->%s: Not support target language", text)

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
                    constructed_url, params=params, headers=headers, json=body, timeout=10
                )
                resp.raise_for_status()
                translated_text = resp.json()[0]["translations"][0]["text"]
            # [{'detectedLanguage': {'language': 'en', 'score': 1.0}, 'translations': [{'text': '你好，我叫约翰。', 'to': 'zh-Hans'}]}]
        except Exception as e:
            logging.error("MicrosoftTranslator Error ->%s:%s", text, e)
        finally:
            return {'result': translated_text, "characters": len(text)}
