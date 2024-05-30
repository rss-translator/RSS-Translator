from django.db import models
from .base import OpenAIInterface
from django.utils.translation import gettext_lazy as _


class GroqTranslator(OpenAIInterface):
    # https://platform.moonshot.cn/docs/api-reference
    base_url = models.URLField(_("API URL"), default="https://api.groq.com/openai/v1")
    model = models.CharField(
        max_length=100,
        default="llama3-8b-8192",
        help_text="More models can be found at https://console.groq.com/docs/models",
    )

    class Meta:
        verbose_name = "Groq"
        verbose_name_plural = "Groq"
