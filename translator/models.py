import logging
import uuid
import json
from time import sleep

import cityhash
import deepl
from PyDeepLX import PyDeepLX
import anthropic
import httpx
from django.db import models
from encrypted_model_fields.fields import EncryptedCharField
from openai import OpenAI, AzureOpenAI
import google.generativeai as genai
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

    def min_size(self):
        if hasattr(self, "max_characters"):
            return self.max_characters * 0.7
        if hasattr(self, "max_tokens"):
            return self.max_tokens * 0.7
        return 0

    def max_size(self):
        if hasattr(self, "max_characters"):
            return self.max_characters * 0.9
        if hasattr(self, "max_tokens"):
            return self.max_tokens * 0.9
        return 0
    def validate(self) -> bool:
        raise NotImplementedError(
            "subclasses of TranslatorEngine must provide a validate() method"
        )

    @classmethod
    def is_translated(cls, text, target_language):
        text_hash = cityhash.CityHash64(f"{text}{target_language}").to_bytes(8, byteorder='little')
        try:
            content = Translated_Content.objects.get(hash=text_hash)
            # logging.info("Using cached translations:%s", text)
            return {
                'result': content.translated_content,
                'tokens': content.tokens,
                'characters': content.characters
            }
        except Translated_Content.DoesNotExist:
            logging.info("Does not exist in cache:%s", text)
            return None

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class TestTranslator(TranslatorEngine):
    translated_text = models.TextField(default="@@Translated Text@@")
    max_characters = models.IntegerField(default=50000)
    interval = models.IntegerField(_("Request Interval(s)"), default=3)

    class Meta:
        verbose_name = "Test"
        verbose_name_plural = "Test"

    def validate(self):
        return True

    def translate(self, text, target_language):
        logging.info(">>> Test Translate [%s]: %s", target_language, text)
        sleep(self.interval)
        return {'result': f"{target_language} {self.translated_text} {text}", "tokens": 0, "characters": len(text)}

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
    prompt = models.TextField(
        default="Translate only the text from the following into {target_language},only returns translations.\n{text}")
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
        logging.info(">>> OpenAI Translate [%s]:", target_language)
        client = self._init()
        tokens = 0
        translated_text = ''
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
                translated_text = ''
                logging.info("OpenAITranslator->%s: finish_reason: %s", text, res.choices[0].finish_reason)
            tokens = res.usage.total_tokens
        except Exception as e:
            logging.error("OpenAITranslator->%s: %s", text, e)

        return {'result': translated_text, "tokens": tokens}

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
        logging.info(">>> AzureAI Translate [%s]:", target_language)
        client = self._init()
        tokens = 0
        translated_text = ''
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
                translated_text = ''
                logging.info("AzureAITranslator->%s: finish_reason: %s", text, res.choices[0].finish_reason)
            tokens = res.usage.total_tokens
        except Exception as e:
            logging.error("AzureAITranslator->%s: %s", text, e)

        return {'result': translated_text, "tokens": tokens, "characters": len(text)}


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
        return deepl.Translator(self.api_key, server_url=self.server_url, proxy=self.proxy)

    def validate(self) -> bool:
        try:
            translator = self._init()
            usage = translator.get_usage()
            return usage.character.valid
        except Exception as e:
            return False

    def translate(self, text, target_language):
        logging.info(">>> DeepL Translate [%s]: %s", target_language, text)
        target_code = self.language_code_map.get(target_language, None)
        translated_text = ''
        try:
            if target_code is None:
                logging.error("DeepLTranslator->%s: Not support target language", text)
            translator = self._init()
            resp = translator.translate_text(text, target_lang=target_code, preserve_formatting=True,
                                             split_sentences='nonewlines')
            translated_text = resp.text
        except Exception as e:
            logging.error("DeepLTranslator->%s: %s", text, e)
        return {'result': translated_text, "characters": len(text)}


class DeepLXTranslator(TranslatorEngine):
    # https://github.com/OwO-Network/DeepLX
    deeplx_api = models.CharField(max_length=255, default="http://127.0.0.1:1188/translate")
    max_characters = models.IntegerField(default=50000)
    interval = models.IntegerField(_("Request Interval(s)"), default=3)
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
        verbose_name = "DeepLX"
        verbose_name_plural = "DeepLX"

    def validate(self) -> bool:
        try:
            resp = self.translate("Hello World", "Chinese Simplified")
            return resp.get("result") != ""
        except Exception as e:
            return False

    def translate(self, text, target_language):
        logging.info(">>> DeepLX Translate [%s]: %s", target_language, text)
        target_code = self.language_code_map.get(target_language, None)
        translated_text = ''
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
            translated_text = resp.json()["data"]
        except Exception as e:
            logging.error("DeepLXTranslator->%s: %s", text, e)
        finally:
            sleep(self.interval)
            return {'result': translated_text, "characters": len(text)}


class DeepLWebTranslator(TranslatorEngine):
    # https://github.com/OwO-Network/PyDeepLX
    max_characters = models.IntegerField(default=50000)
    interval = models.IntegerField(_("Request Interval(s)"), default=5)
    proxy = models.URLField(_("Proxy(optional)"), null=True, blank=True, default=None)
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
        verbose_name = "DeepL Web"
        verbose_name_plural = "DeepL Web"

    def validate(self) -> bool:
        try:
            resp = self.translate("Hello World", "Chinese Simplified")
            return resp.get("result") != ""
        except Exception as e:
            return False

    def translate(self, text, target_language):
        logging.info(">>> DeepL Web Translate [%s]: %s", target_language, text)
        target_code = self.language_code_map.get(target_language, None)
        translated_text = ''
        try:
            if target_code is None:
                logging.error("DeepLWebTranslator->%s: Not support target language", text)

            translated_text = PyDeepLX.translate(text=text, targetLang=target_code, sourceLang="auto",
                                                 proxies=self.proxy)
        except Exception as e:
            logging.error("DeepLWebTranslator->%s: %s", text, e)
        finally:
            sleep(self.interval)
            return {'result': translated_text, "characters": len(text)}

class MicrosoftTranslator(TranslatorEngine):
    # https://learn.microsoft.com/en-us/azure/ai-services/translator/language-support
    api_key = EncryptedCharField(_("API Key"), max_length=255)
    location = models.CharField(max_length=100)
    endpoint = models.CharField(max_length=255, default="https://api.cognitive.microsofttranslator.com")
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
        return result.get("result") != ""

    def translate(self, text, target_language) -> dict:
        logging.info(">>> Microsoft Translate [%s]: %s", target_language, text)
        target_code = self.language_code_map.get(target_language, None)
        translated_text = ''
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
            logging.error("MicrosoftTranslator->%s:%s", text, e)
        finally:
            return {'result': translated_text, "characters": len(text)}


class CaiYunTranslator(TranslatorEngine):
    # https://docs.caiyunapp.com/blog/2018/09/03/lingocloud-api/
    token = EncryptedCharField(max_length=255)
    url = models.URLField(max_length=255, default="http://api.interpreter.caiyunai.com/v1/translator")
    max_characters = models.IntegerField(default=5000)
    language_code_map = {
        "English": "en",
        "Chinese Simplified": "zh",
        "Japanese": "ja",
        "Korean": "ko",
        "Spanish": "es",
        "French": "fr",
        "Russian": "ru",
    }

    class Meta:
        verbose_name = "CaiYun"
        verbose_name_plural = "CaiYun"

    def validate(self) -> bool:
        result = self.translate("Hi", "Chinese Simplified")
        return result.get("result") != ""

    def translate(self, text: str, target_language) -> dict:
        logging.info(">>> CaiYun Translate [%s]: %s", target_language, text)
        target_code = self.language_code_map.get(target_language, None)
        translated_text = ''
        try:
            if target_code is None:
                logging.error("CaiYunTranslator->%s: Not support target language", text)

            payload = {
                "source": text,
                "trans_type": f"auto2{target_code}",
                "request_id": uuid.uuid4().hex,
                "detect": True,
            }

            headers = {
                "content-type": "application/json",
                "x-authorization": f"token {self.token}",
            }

            resp = httpx.post(url=self.url, headers=headers, data=json.dumps(payload), timeout=10)
            resp.raise_for_status()
            translated_text = resp.json()["target"]
        except Exception as e:
            logging.error("CaiYunTranslator->%s:%s", text, e)
        finally:
            return {'result': translated_text, "characters": len(text)}


class GeminiTranslator(TranslatorEngine):
    # https://ai.google.dev/tutorials/python_quickstart
    gemini_models = ['gemini-pro']

    # base_url = models.URLField(_("API URL"), default="https://generativelanguage.googleapis.com/v1beta/")
    api_key = EncryptedCharField(_("API Key"), max_length=255)
    model = models.CharField(max_length=100, default="gemini-pro", choices=[(x, x) for x in gemini_models])
    prompt = models.TextField(
        default="Translate only the text from the following into {target_language},only returns translations.\n{text}")
    temperature = models.FloatField(default=0.5)
    top_p = models.FloatField(default=1)
    top_k = models.IntegerField(default=1)
    max_tokens = models.IntegerField(default=1000)
    interval = models.IntegerField(_("Request Interval(s)"), default=3)

    class Meta:
        verbose_name = "Google Gemini"
        verbose_name_plural = "Google Gemini"

    def _init(self):
        genai.configure(api_key=self.api_key)
        return genai.GenerativeModel(self.model)

    def validate(self):
        if self.api_key:
            try:
                model = self._init()
                res = model.generate_content("hi")
                return res.candidates[0].finish_reason.name == "STOP"
            except Exception as e:
                return False

    def translate(self, text, target_language):
        logging.info(">>> Gemini Translate [%s]:", target_language)
        model = self._init()
        tokens = 0
        translated_text = ''
        try:
            prompt = self.prompt.format(target_language=target_language, text=text)
            generation_config = genai.types.GenerationConfig(
                candidate_count=1,
                temperature=self.temperature,
                top_p=self.top_p,
                top_k=self.top_k,
                max_output_tokens=self.max_tokens
            )
            res = model.generate_content(prompt, generation_config=generation_config)
            if res.candidates[0].finish_reason.name == "STOP":
                translated_text = res.text
            else:
                translated_text = ''
                logging.info("GeminiTranslator->%s: finish_reason: %s", text, res.candidates[0].finish_reason.name)
            tokens = model.count_tokens(prompt).total_tokens
        except Exception as e:
            logging.error("GeminiTranslator->%s: %s", text, e)
        finally:
            sleep(self.interval)

        return {'result': translated_text, "tokens": tokens}


class ClaudeTranslator(TranslatorEngine):
    # https://docs.anthropic.com/claude/reference/getting-started-with-the-api
    claude_models = ['claude-instant-1.2', 'claude-2.1', 'claude-2.0']
    model = models.CharField(max_length=50, default="claude-instant-1.2", choices=[(x, x) for x in claude_models])
    api_key = EncryptedCharField(_("API Key"), max_length=255)
    max_tokens = models.IntegerField(default=1000)
    base_url = models.URLField(_("API URL"), default="https://api.anthropic.com")
    prompt = models.TextField(
        default="Translate only the text from the following into {target_language},only returns translations.\n{text}")
    proxy = models.URLField(_("Proxy(optional)"), null=True, blank=True, default=None)
    temperature = models.FloatField(default=0.7)
    top_p = models.FloatField(null=True, blank=True, default=0.7)
    top_k = models.IntegerField(default=1)

    class Meta:
        verbose_name = "Anthropic Claude"
        verbose_name_plural = "Anthropic Claude"

    def _init(self):
        return anthropic.Anthropic(
            api_key=self.api_key,
            base_url=self.base_url,
            proxies=self.proxy,
        )

    def validate(self):
        if self.api_key:
            try:
                res = self.translate("hi", "Chinese Simplified")
                return res.get("result") != ""
            except Exception as e:
                return False

    def translate(self, text, target_language):
        logging.info(">>> Claude Translate [%s]:", target_language)
        client = self._init()
        tokens = client.count_tokens(text)
        translated_text = ''
        try:
            prompt = self.prompt.format(target_language=target_language, text=text)
            res = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                top_p=self.top_p,
                top_k=self.top_k,
            )
            result = res.content
            if result[0].type == "text":
                translated_text = result[0].text
                tokens += res.usage.output_tokens
        except Exception as e:
            logging.error("ClaudeTranslator->%s: %s", text, e)
        finally:
            return {'result': translated_text, "tokens": tokens}


class GoogleTranslateWebTranslator(TranslatorEngine):
    base_url = models.URLField(_("URL"), default="https://translate.googleapis.com/translate_a/t")
    proxy = models.URLField(_("Proxy(optional)"), null=True, blank=True, default=None)
    interval = models.IntegerField(_("Request Interval(s)"), default=3)
    max_characters = models.IntegerField(default=5000)
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

    def validate(self):
        results = self.translate("hi", "Chinese Simplified")
        return results.get("result") != ""

    def translate(self, text, target_language):
        logging.info(">>> Google Translate Web Translate [%s]:", target_language)
        target_language = self.language_code_map.get(target_language)
        translated_text = ''
        if target_language is None:
            logging.error("GoogleTranslateWebTranslator->%s: Not support target language", text)
            return {'result': translated_text, "characters": len(text)}
        try:
            params = {
                "client": "gtx",
                "sl": "auto",
                "tl": target_language,
                "dt": "t",
                "q": text,
            }
            resp = httpx.get(self.base_url, params=params, timeout=10, proxy=self.proxy)
            resp.raise_for_status()
            translated_text = resp.json()[0][0]
        except Exception as e:
            logging.error("GoogleTranslateWebTranslator->%s: %s", text, e)
        finally:
            sleep(self.interval)
            return {'result': translated_text, "characters": len(text)}
