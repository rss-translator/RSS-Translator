import logging
import uuid
import json

import cityhash
import deepl
import httpx
from django.db import models
from encrypted_model_fields.fields import EncryptedCharField
from openai import OpenAI, AzureOpenAI
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
    openai_models = [
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-16k",
        "gpt-4",
        "gpt-4-32k",
    ]

    api_key = EncryptedCharField(_("API Key"), max_length=255)
    base_url = models.URLField(_("API URL"), default="https://api.openai.com/v1")
    model = models.CharField(max_length=100, default="gpt-3.5-turbo", choices=[(x, x) for x in openai_models])
    prompt = models.TextField(default="Translate the following to {target_language},only returns translations.\n{text}")
    temperature = models.FloatField(default=0.5)
    top_p = models.FloatField(default=0.95)
    frequency_penalty = models.FloatField(default=0)
    presence_penalty = models.FloatField(default=0)
    max_tokens = models.IntegerField(default=1000)

    class Meta:
        verbose_name = "OpenAI"
        verbose_name_plural = "OpenAI"
    
    def _init(self):
        return OpenAI(
                    api_key=self.api_key,
                    base_url = self.base_url,
                    timeout=20.0,
                )

    def validate(self):
        if self.api_key:
            try:
                client = self._init()
                res = client.with_options(max_retries=3).chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": 'Hi'}],
                    max_tokens=10,
                )
                return True
            except Exception as e:
                return False

    def translate(self, text, target_language):
        logging.debug(">>> OpenAI Translate [%s]:", target_language)
        client = self._init()
        tokens = 0
        translated_text = ""
        try:
            prompt = self.prompt.format(target_language=target_language, text=text)
            res = client.with_options(max_retries=3).chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                top_p=self.top_p,
                frequency_penalty=self.frequency_penalty,
                presence_penalty=self.presence_penalty,
                max_tokens=self.max_tokens,
            )
            if res.choices[0].finish_reason == "stop":
                translated_text = res.choices[0].message.content
            else:
                translated_text = text
                logging.info("OpenAITranslator->%s: finish_reason: %s", text, res.choices[0].finish_reason)
            tokens = res.usage.total_tokens
        except Exception as e:
            logging.error("OpenAITranslator->%s: %s", text, e)

        return {'result': translated_text, "tokens": tokens, "characters": len(text)}

class AzureAITranslator(TranslatorEngine):
    # https://learn.microsoft.com/azure/ai-services/openai/
    api_key = EncryptedCharField(_("API Key"), max_length=255)
    endpoint = models.URLField(_("Endpoint"), default="https://example.openai.azure.com/")
    version = models.CharField(max_length=50, default="2023-12-01-preview")
    deloyment_name = models.CharField(max_length=100)
    prompt = models.TextField(default="Translate the following to {target_language},only returns translations.\n{text}")
    temperature = models.FloatField(default=0.5)
    top_p = models.FloatField(default=0.95)
    frequency_penalty = models.FloatField(default=0)
    presence_penalty = models.FloatField(default=0)
    max_tokens = models.IntegerField(default=1000)

    class Meta:
        verbose_name = "Azure OpenAI"
        verbose_name_plural = "Azure OpenAI"
    
    def _init(self):
        return AzureOpenAI(
                    api_key=self.api_key,
                    api_version=self.version,
                    azure_endpoint=self.endpoint,
                    timeout=20.0,
                )

    def validate(self):
        if self.api_key:
            try:
                client = self._init()
                res = client.with_options(max_retries=3).chat.completions.create(
                    model=self.deloyment_name,
                    messages=[{"role": "user", "content": 'Hi'}],
                    max_tokens=10,
                )
                return True
            except Exception as e:
                return False

    def translate(self, text, target_language):
        logging.debug(">>> AzureAI Translate [%s]:", target_language)
        client = self._init()
        tokens = 0
        translated_text = ""
        try:
            prompt = self.prompt.format(target_language=target_language, text=text)
            res = client.with_options(max_retries=3).chat.completions.create(
                model=self.deloyment_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                top_p=self.top_p,
                frequency_penalty=self.frequency_penalty,
                presence_penalty=self.presence_penalty,
                max_tokens=self.max_tokens,
            )
            if res.choices[0].finish_reason == "stop":
                translated_text = res.choices[0].message.content
            else:
                translated_text = text
                logging.info("AzureAITranslator->%s: finish_reason: %s", text, res.choices[0].finish_reason)
            tokens = res.usage.total_tokens
        except Exception as e:
            logging.error("AzureAITranslator->%s: %s", text, e)

        return {'result': translated_text, "tokens": tokens, "characters": len(text)}
    


class DeepLTranslator(TranslatorEngine):
    # https://github.com/DeepLcom/deepl-python
    api_key = EncryptedCharField(_("API Key"), max_length=255)
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
        translated_text = ""
        try:
            if target_code is None:
                logging.error("DeepLTranslator->%s: Not support target language", text)
            translator = deepl.Translator(self.api_key)
            resp = translator.translate_text(text, target_lang=target_code)
            translated_text = resp.text
        except Exception as e:
            logging.error("DeepLTranslator->%s: %s", text, e)
        return {'result': translated_text, "characters": len(text)}


class DeepLXTranslator(TranslatorEngine):
    # https://github.com/OwO-Network/DeepLX
    deeplx_api = models.CharField(max_length=255, default="http://127.0.0.1:1188/translate")
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
        verbose_name = "DeepLX"
        verbose_name_plural = "DeepLX"

    def validate(self) -> bool:
        try:
            resp = self.translate("Hello World", "Chinese Simplified")
            if resp.get('result') != "":
                return True
        except Exception as e:
            return False

    def translate(self, text, target_language):
        logging.debug(">>> DeepLX Translate [%s]: %s", target_language, text)
        target_code = self.language_code_map.get(target_language, None)
        translated_text = ""
        try:
            if target_code is None:
                logging.error("DeepLXTranslator->%s: Not support target language", text)

            data = {
                "text": text,
                "source_lang": "auto",
                "target_lang": target_code,
            }
            post_data = json.dumps(data)
            resp = httpx.post(url=self.deeplx_api, data=post_data, timeout=10)
            if resp.status_code == 429:
                raise ("DeepLXTranslator-> IP has been blocked by DeepL temporarily")
            resp = json.loads(resp.text)
            translated_text = resp.get("data", "")
        except Exception as e:
            logging.error("DeepLXTranslator->%s: %s", text, e)
        return {'result': translated_text, "characters": len(text)}


class MicrosoftTranslator(TranslatorEngine):
    # https://learn.microsoft.com/en-us/azure/ai-services/translator/language-support
    api_key = EncryptedCharField(_("API Key"), max_length=255)
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
