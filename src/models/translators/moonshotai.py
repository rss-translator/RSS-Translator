from django.db import models
from .base import OpenAIInterface
from django.utils.translation import gettext_lazy as _


class MoonshotAITranslator(OpenAIInterface):
    # https://platform.moonshot.cn/docs/api-reference
    base_url = models.URLField(_("API URL"), default="https://api.moonshot.cn/v1")
    model = models.CharField(
        max_length=100,
        default="moonshot-v1-8k",
        help_text="e.g. moonshot-v1-8k, moonshot-v1-32k, moonshot-v1-128k",
    )

    class Meta:
        verbose_name = "Moonshot AI"
        verbose_name_plural = "Moonshot AI"
