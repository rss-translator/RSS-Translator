import logging
import json
import httpx
from .base import TranslatorEngine
from django.utils.translation import gettext_lazy as _
from django.db import models
from config import settings
from encrypted_model_fields.fields import EncryptedCharField


class KagiTranslator(TranslatorEngine):
    # https://docs.Kagi.club/
    api_key = EncryptedCharField(max_length=255)
    url = models.URLField(
        max_length=255, default="https://kagi.com/api/v0",help_text=_("We'll use fastgpt for the translation and summarise for the summary")
    )
    is_ai = models.BooleanField(default=True)
    summarization_engine = models.CharField(max_length=20,default="cecil",help_text="Please check https://help.kagi.com/kagi/api/summarizer.html#summarization-engines")
    summary_type = models.CharField(max_length=20,default="summary",help_text="Please check https://help.kagi.com/kagi/api/summarizer.html#summary-types")
    translate_prompt = models.TextField(
        _("Title Translate Prompt"), default=settings.default_title_translate_prompt
    )
    content_translate_prompt = models.TextField(
        _("Content Translate Prompt"), default=settings.default_content_translate_prompt
    )
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

    class Meta:
        verbose_name = "Kagi"
        verbose_name_plural = "Kagi"

    def validate(self) -> bool:
        try:
            headers = {"content-type": "application/json",'Authorization': f'Bot {self.api_key}'}
            resp = httpx.post(
                url=self.url + "/fastgpt",
                headers=headers,
                data=json.dumps({"query": "Hi"}),
                timeout=10,
            )
            resp.raise_for_status()
            results = resp.json()
            logging.info(results)
            return results.get("data",[]).get("output") is not None
        except Exception as e:
            logging.error("KagiTranslator Validate->%s", e)
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
            self.translate_prompt
            if text_type == "title"
            else self.content_translate_prompt
        )
        try:
            system_prompt = system_prompt.replace("{target_language}", target_language)
            if user_prompt is not None:
                system_prompt += f"\n\n{user_prompt}"

            headers = {"content-type": "application/json",'Authorization': f'Bot {self.api_key}'}
            resp = httpx.post(
                url=self.url + "/fastgpt",
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
            logging.error("KagiTranslator->%s: %s", e, text)
        finally:
            return {"text": translated_text, "tokens": tokens}

    def summarize(self, text: str, target_language: str) -> dict:
        logging.info(">>> Kagi Universal Summarizer [%s]:", target_language)
        tokens = 0
        summarized_text = ""
        
        target_code = self.language_code_map.get(target_language, None)
        try:
            if target_code is None:
                logging.error(
                    "Kagi Universal Summarizer->Not support target language:%s", target_language
                )
            headers = {"content-type": "application/json",'Authorization': f'Bot {self.api_key}'}
            resp = httpx.post(
                url=self.url + "/summarize",
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
            logging.error("KagiTranslator->%s: %s", e, text)
        finally:
            return {"text": summarized_text, "tokens": tokens}

