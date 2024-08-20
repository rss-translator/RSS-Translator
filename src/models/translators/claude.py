import anthropic
import logging
from sqlalchemy import Column, String
from sqlalchemy_utils import URLType
from sqlalchemy.orm import mapped_column
from src.models.core import OpenAIInterface

class Claude(OpenAIInterface):
    model = mapped_column(String(100), default="claude-3-haiku-20240307", nullable=False, use_existing_column=True)
    base_url = mapped_column(URLType, default="https://api.anthropic.com", nullable=False, use_existing_column=True)
    proxy = Column(URLType, nullable=True)

    __mapper_args__ = {
        'polymorphic_identity': 'Claude'
    }

    @property
    def client(self):
        return anthropic.Anthropic(
            api_key=self.api_key,
            base_url=self.base_url,
            proxies=self.proxy,
        )

    def validate(self) -> bool:
        if self.api_key:
            try:
                res = self.translate("Hi", "Chinese Simplified")
                return res.get("text") != ""
            except Exception as e:
                logging.error("Claude validate ->%s", e)
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
        logging.info(">>> Claude Translate [%s]:", target_language)

        tokens = self.client.count_tokens(text)
        translated_text = ""
        system_prompt = (
            system_prompt or self.translate_prompt
            if text_type == "title"
            else self.content_translate_prompt
        )
        try:
            system_prompt = system_prompt.replace("{target_language}", target_language)
            if user_prompt:
                system_prompt += f"\n\n{user_prompt}"

            res = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": text}],
                temperature=self.temperature,
                top_p=self.top_p,
            )
            result = res.content
            if result and result[0].type == "text":
                translated_text = result[0].text
            else:
                logging.warning("Claude-> %s", res.stop_reason)
            tokens = res.usage.output_tokens + res.usage.input_tokens
        except Exception as e:
            logging.error("Claude->%s: %s", e, text)

        return {"text": translated_text, "tokens": tokens}

    def summarize(self, text: str, target_language: str) -> dict:
        logging.info(">>> Claude Summarize [%s]:", target_language)
        return self.translate(text, target_language, system_prompt=self.summary_prompt)
