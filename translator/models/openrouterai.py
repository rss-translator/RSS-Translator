from django.db import models
from .base import OpenAIInterface
from django.utils.translation import gettext_lazy as _

class OpenRouterAITranslator(OpenAIInterface):
    # https://openrouter.ai/docs
    base_url = models.URLField(_("API URL"), default="https://openrouter.ai/api/v1")
    model = models.CharField(max_length=100, default="openai/gpt-3.5-turbo",help_text="More models can be found at https://openrouter.ai/docs#models")
    
    class Meta:
        verbose_name = "OpenRouter AI"
        verbose_name_plural = "OpenRouter AI"
        