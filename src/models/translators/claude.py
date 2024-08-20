import anthropic
from config import settings
from .base import TranslatorEngine
import logging
from django.db import models
from encrypted_model_fields.fields import EncryptedCharField
from django.utils.translation import gettext_lazy as _


class ClaudeTranslator(TranslatorEngine):
    # https://docs.anthropic.com/claude/reference/getting-started-with-the-api
    is_ai = models.BooleanField(default=True, editable=False)
    model = models.CharField(
        max_length=50,
        default="claude-3-haiku-20240307",
        help_text="e.g. claude-3-haiku-20240307, claude-3-sonnet-20240229, claude-3-opus-20240229",
    )
    api_key = EncryptedCharField(_("API Key"), max_length=255)
    max_tokens = models.IntegerField(default=1000)
    base_url = models.URLField(_("API URL"), default="https://api.anthropic.com")
    translate_prompt = models.TextField(
        _("Title Translate Prompt"), default=settings.default_title_translate_prompt
    )
    content_translate_prompt = models.TextField(
        _("Content Translate Prompt"), default=settings.default_content_translate_prompt
    )

    proxy = models.URLField(_("Proxy(optional)"), null=True, blank=True, default=None)
    temperature = models.FloatField(default=0.7)
    top_p = models.FloatField(null=True, blank=True, default=0.7)
    top_k = models.IntegerField(default=1)

    summary_prompt = models.TextField(default=settings.default_summary_prompt)

    class Meta:
        verbose_name = "Anthropic Claude"
        verbose_name_plural = "Anthropic Claude"

    def _init(self):
        return anthropic.Anthropic(
            api_key=self.api_key,
            base_url=self.base_url,
            proxies=self.proxy,
        )

    def validate(self) -> bool:
        if self.api_key:
            res = self.translate("hi", "Chinese Simplified")
            return res.get("text") != ""

    def translate(
        self,
        text: str,
        target_language: str,
        system_prompt: str = None,
        user_prompt: str = None,
        text_type: str = "title",
        **kwargs
    ) -> dict:
        logging.info(">>> Claude Translate [%s]:", target_language)
        client = self._init()
        tokens = client.count_tokens(text)
        translated_text = ""
        system_prompt = (
            system_prompt or self.translate_prompt
            if text_type == "title"
            else self.content_translate_prompt
        )
        try:
            system_prompt = system_prompt.replace("{target_language}", target_language)
            if user_prompt is not None:
                system_prompt += f"\n\n{user_prompt}"

            res = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": text}],
                temperature=self.temperature,
                top_p=self.top_p,
                top_k=self.top_k,
            )
            result = res.content
            if result and result[0].type == "text":
                translated_text = result[0].text
            else:
                logging.warning("ClaudeTranslator-> %s", res.stop_reason)
            tokens = res.usage.output_tokens + res.usage.input_tokens
        except Exception as e:
            logging.error("ClaudeTranslator->%s: %s", e, text)
        finally:
            return {"text": translated_text, "tokens": tokens}

    def summarize(self, text: str, target_language: str) -> dict:
        logging.info(">>> Claude Summarize [%s]:", target_language)
        return self.translate(text, target_language, system_prompt=self.summary_prompt)
