
import logging
from django.contrib import admin
#from django.conf import settings
#from .models import *

#from django.utils.translation import gettext_lazy  as _

from utils.modelAdmin_utils import valid_icon

class BaseTranslatorAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        logging.info("Call save_model: %s", obj)
        obj.valid = None
        obj.save()
        try:
            obj.valid = obj.validate()
        except Exception as e:
            obj.valid = False
            logging.error("Error in translator: %s", e)
        finally:
            obj.save()

    def is_valid(self, obj):
        return valid_icon(obj.valid)

    is_valid.short_description = 'Valid'

    def masked_api_key(self, obj):
        api_key = obj.api_key if hasattr(obj, "api_key") else obj.token
        if api_key:
            return f"{api_key[:3]}...{api_key[-3:]}"
        return ""
    masked_api_key.short_description = "API Key"

'''
@admin.register(OpenAITranslator)
class OpenAITranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "api_key", "base_url", "model", "translate_prompt", "summary_prompt", "temperature", "top_p", "frequency_penalty",
              "presence_penalty", "max_tokens"]
    list_display = ["name", "is_valid", "masked_api_key", "model", "translate_prompt",  "summary_prompt", "max_tokens", "base_url"]


@admin.register(AzureAITranslator)
class AzureAITranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "api_key", "base_url", "version", "model", "translate_prompt", "summary_prompt", "temperature", "top_p",
              "frequency_penalty", "presence_penalty", "max_tokens"]
    list_display = ["name", "is_valid", "masked_api_key", "model", "version", "translate_prompt", "summary_prompt", "max_tokens", "base_url"]


@admin.register(DeepLTranslator)
class DeepLTranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "api_key", "server_url", "proxy", "max_characters"]
    list_display = ["name", "is_valid", "masked_api_key", "server_url", "proxy", "max_characters"]


@admin.register(DeepLXTranslator)
class DeepLXTranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "deeplx_api", "interval", "max_characters"]
    list_display = ["name", "is_valid", "deeplx_api", "interval", "max_characters"]


# @admin.register(DeepLWebTranslator)
class DeepLWebTranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "interval", "proxy", "max_characters"]
    list_display = ["name", "is_valid", "interval", "proxy", "max_characters"]

@admin.register(MicrosoftTranslator)
class MicrosoftTranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "api_key", "location", "endpoint", "max_characters"]
    list_display = ["name", "is_valid", "masked_api_key", "location", "endpoint", "max_characters"]


@admin.register(CaiYunTranslator)
class CaiYunTranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "token", "url", "max_characters"]
    list_display = ["name", "is_valid", "masked_api_key", "url", "max_characters"]


@admin.register(GeminiTranslator)
class GeminiTranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "api_key", "model", "translate_prompt", "summary_prompt", "temperature", "top_p", "top_k", "max_tokens",  "interval"]
    list_display = ["name", "is_valid", "masked_api_key", "model", "translate_prompt", "summary_prompt", "max_tokens",  "interval"]


@admin.register(GoogleTranslateWebTranslator)
class GoogleTranslateWebTranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "base_url", "interval", "proxy", "max_characters"]
    list_display = ["name", "is_valid", "base_url", "proxy", "interval", "max_characters"]

@admin.register(ClaudeTranslator)
class ClaudeTranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "api_key", "base_url", "model", "translate_prompt", "summary_prompt", "temperature", "top_p", "top_k", "max_tokens",  "proxy"]
    list_display = ["name", "is_valid", "masked_api_key", "model", "translate_prompt", "summary_prompt", "max_tokens", "base_url"]

@admin.register(MoonshotAITranslator)
class MoonshotAITranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "api_key", "base_url", "model", "translate_prompt", "summary_prompt", "temperature", "top_p", "frequency_penalty",
              "presence_penalty", "max_tokens"]
    list_display = ["name", "is_valid", "masked_api_key", "model", "translate_prompt", "summary_prompt", "max_tokens", "base_url"]

@admin.register(TogetherAITranslator)
class TogetherAITranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "api_key", "base_url", "model", "translate_prompt", "summary_prompt", "temperature", "top_p", "frequency_penalty",
              "presence_penalty", "max_tokens"]
    list_display = ["name", "is_valid", "masked_api_key", "model", "translate_prompt", "summary_prompt", "max_tokens", "base_url"]

@admin.register(OpenRouterAITranslator)
class OpenRouterAITranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "api_key", "base_url", "model", "translate_prompt", "summary_prompt", "temperature", "top_p", "frequency_penalty",
              "presence_penalty", "max_tokens"]
    list_display = ["name", "is_valid", "masked_api_key", "model", "translate_prompt", "summary_prompt", "max_tokens", "base_url"]

@admin.register(GroqTranslator)
class GroqTranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "api_key", "base_url", "model", "translate_prompt", "summary_prompt", "temperature", "top_p", "frequency_penalty",
              "presence_penalty", "max_tokens"]
    list_display = ["name", "is_valid", "masked_api_key", "model", "translate_prompt", "summary_prompt", "max_tokens", "base_url"]
'''         



class Translated_ContentAdmin(admin.ModelAdmin):
    fields = ["original_content", "translated_content", "translated_language", "tokens", "characters"]
    list_display = ["original_content", "translated_language", "translated_content", "tokens", "characters"]

    # def has_change_permission(self, request, obj=None):
    #     return False

    # def has_add_permission(self, request):
    #     return False


class TestTranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "translated_text", "max_characters", "interval"]
    list_display = ["name", "is_valid", "translated_text", "max_characters", "interval"]