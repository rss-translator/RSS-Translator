from .base import OpenAIInterface


class OpenAITranslator(OpenAIInterface):
    # https://platform.openai.com/docs/api-reference/chat
    class Meta:
        verbose_name = "OpenAI"
        verbose_name_plural = "OpenAI"
