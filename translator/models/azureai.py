from django.db import models
from django.utils.translation import gettext_lazy as _
from openai import AzureOpenAI
from .base import OpenAIInterface


class AzureAITranslator(OpenAIInterface):
    # https://learn.microsoft.com/azure/ai-services/openai/
    base_url = models.URLField(
        _("Endpoint"), default="https://example.openai.azure.com/"
    )
    version = models.CharField(max_length=50, default="2024-02-15-preview")
    model = models.CharField(
        _("Deloyment Name"), max_length=100, default="Your Deployment Name"
    )

    class Meta:
        verbose_name = "Azure OpenAI"
        verbose_name_plural = "Azure OpenAI"

    def _init(self):
        return AzureOpenAI(
            api_key=self.api_key,
            api_version=self.version,
            azure_endpoint=self.base_url,
            timeout=120.0,
        )
