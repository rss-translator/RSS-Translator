from django.db import models
from .base import OpenAIInterface
from django.utils.translation import gettext_lazy as _


class TogetherAITranslator(OpenAIInterface):
    # https://docs.together.ai/docs/openai-api-compatibility
    base_url = models.URLField(_("API URL"), default="https://api.together.xyz/v1")
    model = models.CharField(
        max_length=100,
        default="mistralai/Mixtral-8x7B-Instruct-v0.1",
        help_text="More models can be found at https://docs.together.ai/docs/inference-models#chat-models",
    )

    class Meta:
        verbose_name = "Together AI"
        verbose_name_plural = "Together AI"
