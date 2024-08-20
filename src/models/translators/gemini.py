from config import settings
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from .base import TranslatorEngine
import logging
from time import sleep
from django.db import models
from encrypted_model_fields.fields import EncryptedCharField
from django.utils.translation import gettext_lazy as _


class GeminiTranslator(TranslatorEngine):
    # https://ai.google.dev/tutorials/python_quickstart
    is_ai = models.BooleanField(default=True, editable=False)
    # base_url = models.URLField(_("API URL"), default="https://generativelanguage.googleapis.com/v1beta/")
    api_key = EncryptedCharField(_("API Key"), max_length=255)
    model = models.CharField(
        max_length=100,
        default="gemini-pro",
        help_text="e.g. gemini-pro, gemini-1.5-pro-latest",
    )
    translate_prompt = models.TextField(
        _("Title Translate Prompt"), default=settings.default_title_translate_prompt
    )
    content_translate_prompt = models.TextField(
        _("Content Translate Prompt"), default=settings.default_content_translate_prompt
    )

    temperature = models.FloatField(default=0.5)
    top_p = models.FloatField(default=1)
    top_k = models.IntegerField(default=1)
    max_tokens = models.IntegerField(default=1000)
    interval = models.IntegerField(_("Request Interval(s)"), default=3)

    summary_prompt = models.TextField(default=settings.default_summary_prompt)

    class Meta:
        verbose_name = "Google Gemini"
        verbose_name_plural = "Google Gemini"

    def _init(self, system_prompt: str = None):
        genai.configure(api_key=self.api_key)
        return genai.GenerativeModel(
            model_name=self.model,
            # system_instruction=system_prompt or self.translate_prompt
        )

    def validate(self) -> bool:
        if self.api_key:
            try:
                model = self._init()
                res = model.generate_content("hi")
                return res.candidates[0].finish_reason == 1
            except Exception as e:
                logging.error("GeminiTranslator validate ->%s", e)
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
        logging.info(">>> Gemini Translate [%s]:", target_language)

        tokens = 0
        translated_text = ""
        system_prompt = (
            system_prompt or self.translate_prompt
            if text_type == "title"
            else self.content_translate_prompt
        )
        prompt = f"{system_prompt.replace('{target_language}', target_language)}\n{user_prompt}\n{text}"
        try:
            model = self._init()
            generation_config = genai.types.GenerationConfig(
                candidate_count=1,
                temperature=self.temperature,
                top_p=self.top_p,
                top_k=self.top_k,
                max_output_tokens=self.max_tokens,
            )
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            }
            res = model.generate_content(prompt, generation_config=generation_config, safety_settings=safety_settings)
            finish_reason = res.candidates[0].finish_reason if res.candidates else None
            if finish_reason == 1:
                translated_text = res.text
            else:
                translated_text = ""
                logging.info(
                    "GeminiTranslator finish_reason->%s: %s", finish_reason.name, text
                )
            tokens = model.count_tokens(prompt).total_tokens
        except Exception as e:
            logging.error("GeminiTranslator->%s: %s", e, text)
        finally:
            sleep(self.interval)

        return {"text": translated_text, "tokens": tokens}

    def summarize(self, text: str, target_language: str) -> dict:
        logging.info(">>> Gemini Summarize [%s]: %s", target_language, text)
        return self.translate(text, target_language, system_prompt=self.summary_prompt)
