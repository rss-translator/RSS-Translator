import httpx
import logging
import uuid

from sqlalchemy import Column, String, Text
from sqlalchemy.orm import mapped_column
from sqlalchemy_utils import URLType
from src.models.core import Engine


class MicrosoftTranslator(Engine):
    # https://learn.microsoft.com/en-us/azure/ai-services/translator/language-support
    api_key = mapped_column(String(255),nullable=False,use_existing_column=True)  
    location = Column(String(100),nullable=False)
    endpoint = Column(String(200),nullable=False, default="https://api.cognitive.microsofttranslator.com"
    )
    max_characters = Column(Integer, default=5000)
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

    __mapper_args__ = {
        'polymorphic_identity': "Microsoft Translator"
    }

    def validate(self) -> bool:
        try:
            result = self.translate("Hi", "Chinese Simplified")
            return result.get("text") != ""
        except Exception as e:
            logging.error("MicrosoftTranslator->%s", e)
        return False

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
