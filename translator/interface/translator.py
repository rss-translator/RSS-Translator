import logging
import uuid

import deepl
import httpx
from openai import OpenAI


class TranslatorInterface:
    def __init__(self, secrets: dict):
        self.secrets = secrets

    def translate(self, text, target_language):
        return {'result': ''}


class MicrosoftTranslator(TranslatorInterface):
    # https://learn.microsoft.com/en-us/azure/ai-services/translator/language-support
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
        "Portuguese (Portugal)": "pt-pt",
        "Swedish": "sv",
        "Turkish": "tr",
    }

    def translate(self, text, target_language):
        logging.debug(">>> Microsoft Translate [%s]: %s", target_language, text)
        target_code = self.language_code_map.get(target_language, None)
        try:
            if target_code is None:
                raise Exception(f"MST->{text}: Not support target language")

            constructed_url = f"{self.secrets['MST_EndPoint']}/translate"
            params = {"api-version": "3.0", "to": target_code}
            headers = {
                "Ocp-Apim-Subscription-Key": self.secrets["MST_Key"],
                "Ocp-Apim-Subscription-Region": self.secrets["MST_Location"],
                "Content-type": "application/json",
                "X-ClientTraceId": str(uuid.uuid4()),
            }
            body = [{"text": text}]

            with httpx.Client() as client:
                resp = client.post(
                    constructed_url, params=params, headers=headers, json=body, timeout=10
                )
            translated_text = resp.json()[0]["translations"][0]["text"]
            # [{'detectedLanguage': {'language': 'en', 'score': 1.0}, 'translations': [{'text': '你好，我叫约翰。', 'to': 'zh-Hans'}]}]
        except Exception:
            raise Exception(f"MST->{text}: {resp.json()['error']}")
        return {'result': translated_text}


class DeepLTranslator(TranslatorInterface):
    # https://www.deepl.com/zh/docs-api/translate-text/multiple-sentences
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
        "Portuguese (Portugal)": "PT-PT",
        "Swedish": "SV",
        "Turkish": "TR",
    }

    def translate(self, text, target_language):
        logging.debug(">>> DeepL Translate [%s]: %s", target_language, text)
        target_code = self.language_code_map.get(target_language, None)
        try:
            if target_code is None:
                raise Exception(f"DeepL->{text}: Not support target language")
            translator = deepl.Translator(self.secrets["Deepl_API_Key"])
            resp = translator.translate_text(text, target_lang=target_code)
            translated_text = resp.text
        except Exception as e:
            raise Exception(f"DeepL->{text}: {e}")
        return {'result': translated_text}


class OpenAITranslator(TranslatorInterface):
    # https://platform.openai.com/docs/api-reference/chat
    def translate(self, text, target_language):
        logging.debug(">>> OpenAI Translate [%s]: %s", target_language, text)
        openai = OpenAI(
            api_key=self.secrets["OpenAI_Key"],
        )
        tokens = 0
        translated_text = ""
        try:
            prompt = f"Translate the following to {target_language},only returns translations.\n{text}"
            res = openai.chat.completions.create(
                model=self.secrets["OpenAI_Model"],
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=1000,
            )
            translated_text = res.choices[0].message.content
            tokens = res.usage.total_tokens
        except Exception as e:
            print(f"OpenAI->{text}: {e}")

        return {'result': translated_text, "tokens": tokens}


class GoogleTranslator(TranslatorInterface):
    language_code_map = {
    }

    def translate(self, text, target_language):
        pass


class TestTranslator(TranslatorInterface):
    def translate(self, text, target_language):
        return {'result': "@This is a test translation.@"}


class TranslatorFactory:
    def __init__(self, secrets: dict):
        self.secrets = secrets
        self.translators = {
            'microsoft translate': MicrosoftTranslator(secrets=self.secrets),
            'google translate': GoogleTranslator(secrets=self.secrets),
            'deepl': DeepLTranslator(secrets=self.secrets),
            'openai': OpenAITranslator(secrets=self.secrets),
            'test': TestTranslator(secrets=self.secrets),
        }

    # @staticmethod
    def get_translator(self, service_name):
        logging.debug("Set [%s] as Translator", service_name)
        return self.translators.get(service_name, None)
