import logging
import uuid
from typing import Optional

import httpx
from lingua import Language, LanguageDetectorBuilder


# https://github.com/komodojp/tinyld
class LanguageDetectorInterface:
    def __init__(self, secrets: dict):
        self.secrets = secrets

    def detect(self, text: str) -> Optional[str]:
        pass


class LinguaDetector(LanguageDetectorInterface):
    languages = {
        Language.ENGLISH: "English",
        Language.CHINESE: "Chinese Simplified",
        Language.JAPANESE: "Japanese",
        Language.RUSSIAN: "Russian",
        Language.KOREAN: "Korean",
        Language.CZECH: "Czech",
        Language.DANISH: "Danish",
        Language.GERMAN: "German",
        Language.SPANISH: "Spanish",
        Language.FRENCH: "French",
        Language.INDONESIAN: "Indonesian",
        Language.ITALIAN: "Italian",
        Language.HUNGARIAN: "Hungarian",
        Language.NYNORSK: "Norwegian Bokmål",
        Language.DUTCH: "Dutch",
        Language.POLISH: "Polish",
        Language.PORTUGUESE: "Portuguese (Portugal)",
        Language.SWEDISH: "Swedish",
        Language.TURKISH: "Turkish",
    }

    def detect(self, text: str) -> Optional[str]:
        detector = LanguageDetectorBuilder.from_languages(*self.languages.keys()).build()
        language = detector.detect_language_of(text)
        logging.debug("<<< Lingua Detect: [%s]%s", language, text)
        return self.languages.get(language)


class MicrosoftDetector(LanguageDetectorInterface):
    language_code_map = {
        "en": "English",
        "zh-Hans": "Chinese Simplified",
        "zh-Hant": "Chinese Traditional",
        "ru": "Russian",
        "ja": "Japanese",
        "ko": "Korean",
        "cs": "Czech",
        "da": "Danish",
        "de": "German",
        "es": "Spanish",
        "fr": "French",
        "id": "Indonesian",
        "it": "Italian",
        "hu": "Hungarian",
        "nb": "Norwegian Bokmål",
        "nl": "Dutch",
        "pl": "Polish",
        "pt-pt": "Portuguese (Portugal)",
        "sv": "Swedish",
        "tr": "Turkish"
    }

    def detect(self, text: str) -> Optional[str]:
        logging.debug("<<< Microsoft Detect: %s", text)
        constructed_url = f"{self.secrets['MST_EndPoint']}/detect"
        params = {"api-version": "3.0"}
        headers = {
            "Ocp-Apim-Subscription-Key": self.secrets["MST_Key"],
            "Ocp-Apim-Subscription-Region": self.secrets["MST_Location"],
            "Content-type": "application/json",
            "X-ClientTraceId": str(uuid.uuid4()),
        }
        body = [{'text': text}]
        with httpx.Client() as client:
            resp = client.post(
                constructed_url, params=params, headers=headers, json=body, timeout=10
            )
        if resp.status_code == 200:
            data = resp.json()[0]['language']
            return self.language_code_map.get(data)
        return None


'''
# It's too old, don't use it
class GuessLanguageDetector(LanguageDetectorInterface):
    # https://github.com/kent37/guess-language
    from guess_language import guess_language
    language_code_map = {
        "en": "English",
        "zh": "Chinese Simplified",
        "zh-tw": "Chinese Traditional",
        "ru": "Russian",
        "ja": "Japanese",
        "ko": "Korean",
        "cs": "Czech",
        "da": "Danish",
        "de": "German",
        "es": "Spanish",
        "fr": "French",
        "id": "Indonesian",
        "it": "Italian",
        "hu": "Hungarian",
        "no": "Norwegian Bokmål",
        "nl": "Dutch",
        "pl": "Polish",
        "pt": "Portuguese (Portugal)",
        "sv": "Swedish",
        "tr": "Turkish"
    }
    def detect(self, text: str) -> Optional[str]:
        if len(text) < 20:
            text += "."
            text = text + (text * (20 // len(text) + 1))
        
        language = guess_language(text)
        return self.language_code_map.get(language)
'''


class DetectorFactory:
    def __init__(self, secrets: dict = {}):
        self.secrets = secrets
        self.detector = {
            "lingua": LinguaDetector(self.secrets),
            "microsoft": MicrosoftDetector(secrets=self.secrets),
        }

    def get_detector(self, detector: str) -> LanguageDetectorInterface:
        if detector == "lingua":
            logging.debug("Set Lingua as detector")
            return self.detector["lingua"]
        if detector == "microsoft":
            logging.debug("Set Microsoft as detector")
            return self.detector["microsoft"]
        logging.error("Not support detector: %s", detector)
        return None
