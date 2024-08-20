from .base import TranslatorEngine
import logging
from config import settings
from django.db import models
from encrypted_model_fields.fields import EncryptedCharField
from django.utils.translation import gettext_lazy as _

from volcenginesdkarkruntime import Ark

class DoubaoTranslator(TranslatorEngine):
    # https://www.volcengine.com/docs/82379/1263482
    is_ai = models.BooleanField(default=True, editable=False)
    api_key = EncryptedCharField(_("API Key"), max_length=255)
    endpoint_id = models.CharField(max_length=255)
    region = models.CharField(max_length=50, default="cn-beijing")
    max_tokens = models.IntegerField(default=4096)
    translate_prompt = models.TextField(
        _("Title Translate Prompt"), default=settings.default_title_translate_prompt
    )
    content_translate_prompt = models.TextField(
        _("Content Translate Prompt"), default=settings.default_content_translate_prompt
    )
    summary_prompt = models.TextField(default=settings.default_summary_prompt)
    class Meta:
        verbose_name = _("Doubao")
        verbose_name_plural = _("Doubao")

    def _init(self):
        return Ark(api_key=self.api_key)

    def validate(self) -> bool:
        try:
            client = self._init()
            completion = client.chat.completions.create(
                model=self.endpoint_id,
                messages=[
                    {"role": "user", "content": "Hi"},
                ],
                max_tokens = 10,
            )
            return True if completion.choices[0].message.content else False
        except Exception as e:
            logging.error("DoubaoTranslator validate ->%s", e)
            return False

    def translate(self, text: str, target_language: str, system_prompt: str = None, user_prompt: str = None,
        text_type: str = "title", **kwargs) -> dict:

        logging.info(">>> Doubao Translate [%s]: %s", target_language, text)
        client = self._init()
        translated_text = ""
        tokens = 0
        system_prompt = (
            system_prompt or self.translate_prompt
            if text_type == "title"
            else self.content_translate_prompt
        )
        try:
            system_prompt = system_prompt.replace("{target_language}", target_language)
            if user_prompt:
                system_prompt += f"\n\n{user_prompt}"

            res = client.chat.completions.create(
                model=self.endpoint_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                max_tokens=self.max_tokens,
            )
            #if res.choices[0].finish_reason.lower() == "stop" or res.choices[0].message.content:
            if res.choices and res.choices[0].message.content:
                translated_text = res.choices[0].message.content
                logging.info("DoubaoTranslator->%s: %s", res.choices[0].finish_reason, translated_text)
            
            tokens = res.usage.total_tokens if res.usage else 0
        except Exception as e:
            logging.error("DoubaoTranslator->%s: %s", e, text)

        return {"text": translated_text, "tokens": tokens}

    def summarize(self, text: str, target_language: str) -> dict:
        logging.info(">>> Doubao Summarize [%s]: %s", target_language, text)
        return self.translate(text, target_language, system_prompt=self.summary_prompt)

