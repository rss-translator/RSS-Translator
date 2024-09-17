import logging
import json
import httpx

from sqlalchemy import Column, String, Text
from sqlalchemy.orm import mapped_column
from sqlalchemy_utils import URLType
from api.models.core import Engine

class Kagi(Engine):
    # https://docs.Kagi.club/
    is_ai = True
    api_key = mapped_column(String(255),nullable=False,use_existing_column=True)  
    base_url = mapped_column(URLType, nullable=False, default="https://kagi.com/api/v0", use_existing_column=True)
    summarization_engine = Column(String(20),nullable=False, default="cecil")
    summary_type = Column(String(20),nullable=False, default="summary")
    title_translate_prompt = mapped_column(Text,nullable=False,use_existing_column=True)
    content_translate_prompt = mapped_column(Text,nullable=False,use_existing_column=True)
    language_code_map = {
            "English": "EN",
            "Chinese Simplified": "ZH",
            "Chinese Traditional": "ZH-HANT",
            "Russian": "RU",
            "Korean": "KO",
            "Japanese": "JA",
            "Czech": "CS",
            "German": "DE",
            "Spanish": "ES",
            "French": "FR",
            "Indonesian": "ID",
            "Hungarian": "HU",
            "Norwegian Bokmal": "NB",
            "Dutch": "NL",
            "Swedish": "SV",
            "Danish": "DA",
            "Turkish": "TR",
            "Italian": "IT",
            "Polish": "PL",
            "Portuguese": "PT",
        }

    __mapper_args__ = {
        'polymorphic_identity': 'Kagi'
    }

    def validate(self) -> bool:
        try:
            headers = {"content-type": "application/json",'Authorization': f'Bot {self.api_key}'}
            resp = httpx.post(
                url=self.base_url + "/fastgpt",
                headers=headers,
                data=json.dumps({"query": "Hi"}),
                timeout=10,
            )
            resp.raise_for_status()
            results = resp.json()
            logging.info(results)
            return results.get("data",[]).get("output") is not None
        except Exception as e:
            logging.error("Kagi Validate->%s", e)
        return False

    def translate(
        self,
        text: str,
        target_language: str,
        system_prompt: str = None,
        user_prompt: str = None,
        text_type: str = "title",
        **kwargs
    ) -> dict:
        logging.info(">>> Kagi FastGPT Translate [%s]:", target_language)
        tokens = 0
        translated_text = ""
        system_prompt = (
            self.title_translate_prompt
            if text_type == "title"
            else self.content_translate_prompt
        )
        try:
            system_prompt = system_prompt.replace("{target_language}", target_language)
            if user_prompt is not None:
                system_prompt += f"\n\n{user_prompt}"

            headers = {"content-type": "application/json",'Authorization': f'Bot {self.api_key}'}
            resp = httpx.post(
                url=self.base_url + "/fastgpt",
                headers=headers,
                data=json.dumps({"query": f"{system_prompt}\n{text}"}),
                timeout=10,
            )
            resp.raise_for_status()
            results = resp.json()
            data = results.get("data",[])
            if data:
                 translated_text = data.get("output")
            tokens = data.get("tokens",0)
        except Exception as e:
            logging.error("Kagi->%s: %s", e, text)

        return {"text": translated_text, "tokens": tokens}

    def summarize(self, text: str, target_language: str) -> dict:
        logging.info(">>> Kagi Universal Summarizer [%s]:", target_language)
        tokens = 0
        summarized_text = ""
        
        target_code = self.language_code_map.get(target_language, None)
        try:
            if target_code is None:
                raise Exception(
                    "Kagi Universal Summarizer->Not support target language:%s", target_language
                )
            headers = {"content-type": "application/json",'Authorization': f'Bot {self.api_key}'}
            resp = httpx.post(
                url=self.base_url + "/summarize",
                headers=headers,
                data=json.dumps({"text": text,"summary_type": self.summary_type, "engine":self.summarization_engine, "target_language":target_code}),
                timeout=10,
            )
            resp.raise_for_status()
            results = resp.json()
            data = results.get("data",[])
            if data:
                 summarized_text = data.get("output")
            tokens = data.get("tokens",0)
        except Exception as e:
            logging.error("Kagi->%s: %s", e, text)

        return {"text": summarized_text, "tokens": tokens}

