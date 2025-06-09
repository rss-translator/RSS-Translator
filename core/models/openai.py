import logging
from django.db import models
from django.utils.translation import gettext_lazy as _
from config import settings
from openai import OpenAI
from encrypted_model_fields.fields import EncryptedCharField
from .translator import Translator


class OpenAITranslator(Translator):
    # https://platform.openai.com/docs/api-reference/chat

    class Meta:
        proxy = True
        verbose_name = "OpenAI"
        verbose_name_plural = "OpenAI"

    def get_client(self):
        config = self.service_config
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.model = config.get("model", "gpt-3.5-turbo")
        self.title_translate_prompt = config.get("title_translate_prompt", settings.default_title_translate_prompt)
        self.content_translate_prompt = config.get("content_translate_prompt", settings.default_content_translate_prompt)
        self.summary_prompt = config.get("summary_prompt", settings.default_summary_prompt)
        self.temperature = config.get("temperature", 0.2)
        self.top_p = config.get("top_p", 0.2)
        self.frequency_penalty = config.get("frequency_penalty", 0)
        self.presence_penalty = config.get("presence_penalty", 0)
        self.max_tokens = config.get("max_tokens", 2000)
    
        return OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=120.0,
            model=self.model,
            title_translate_prompt=self.title_translate_prompt,
            content_translate_prompt=self.content_translate_prompt,
            summary_prompt=self.summary_prompt,
            temperature=self.temperature,
            top_p=self.top_p,
            frequency_penalty=self.frequency_penalty,
            presence_penalty=self.presence_penalty,
            max_tokens=self.max_tokens,
        )

    def validate(self) -> bool:
        if self.api_key:
            try:
                client = self._init()
                res = client.with_options(max_retries=3).chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": "Hi"}],
                    max_tokens=10,
                )
                fr = res.choices[
                    0
                ].finish_reason  # 有些第三方源在key或url错误的情况下，并不会抛出异常代码，而是返回html广告，因此添加该行。
                logging.info(">>> Translator Validate:%s", fr)
                return True
            except Exception as e:
                logging.error("OpenAIInterface validate ->%s", e)
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
        logging.info(">>> Translate [%s]: %s", target_language, text)
        client = self._init()
        tokens = 0
        translated_text = ""
        system_prompt = (
            system_prompt or self.title_translate_prompt
            if text_type == "title"
            else self.content_translate_prompt
        )
        try:
            system_prompt = system_prompt.replace("{target_language}", target_language)
            if user_prompt:
                system_prompt += f"\n\n{user_prompt}"

            res = client.with_options(max_retries=3).chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "https://www.rsstranslator.com",
                    "X-Title": "RSS Translator"
                },
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                temperature=self.temperature,
                top_p=self.top_p,
                frequency_penalty=self.frequency_penalty,
                presence_penalty=self.presence_penalty,
                max_tokens=self.max_tokens,
            )
            #if res.choices[0].finish_reason.lower() == "stop" or res.choices[0].message.content:
            if res.choices and res.choices[0].message.content:
                translated_text = res.choices[0].message.content
                logging.info("OpenAITranslator->%s: %s", res.choices[0].finish_reason, translated_text)
            # else:
            #     translated_text = ''
            #     logging.warning("Translator->%s: %s", res.choices[0].finish_reason, text)
            tokens = res.usage.total_tokens if res.usage else 0
        except Exception as e:
            logging.error("OpenAIInterface->%s: %s", e, text)

        return {"text": translated_text, "tokens": tokens}

    def summarize(self, text: str, target_language: str) -> dict:
        logging.info(">>> Summarize [%s]: %s", target_language, text)
        return self.translate(text, target_language, system_prompt=self.summary_prompt)
