import logging
from django.contrib import admin
from core.admin import core_admin_site

from django.conf import settings
from django.shortcuts import redirect
from .models import *

# from django.utils.translation import gettext_lazy  as _

from utils.modelAdmin_utils import valid_icon


class BaseTranslatorAdmin(admin.ModelAdmin):
    get_model_perms = lambda self, request: {}  # 不显示在admin页面

    def save_model(self, request, obj, form, change):
        logging.info("Call save_model: %s", obj)
        # obj.valid = None
        # obj.save()
        try:
            obj.valid = obj.validate()
        except Exception as e:
            obj.valid = False
            logging.error("Error in translator: %s", e)
        finally:
            obj.save()
        return redirect("/translator")

    def is_valid(self, obj):
        return valid_icon(obj.valid)

    is_valid.short_description = "Valid"

    def masked_api_key(self, obj):
        api_key = obj.api_key if hasattr(obj, "api_key") else obj.token
        if api_key:
            return f"{api_key[:3]}...{api_key[-3:]}"
        return ""

    masked_api_key.short_description = "API Key"

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        # 重定向到指定URL
        return redirect("/translator")


class OpenAITranslatorAdmin(BaseTranslatorAdmin):
    fields = [
        "name",
        "api_key",
        "base_url",
        "model",
        "translate_prompt",
        "content_translate_prompt",
        "summary_prompt",
        "temperature",
        "top_p",
        "frequency_penalty",
        "presence_penalty",
        "max_tokens",
    ]
    list_display = [
        "name",
        "is_valid",
        "masked_api_key",
        "model",
        "translate_prompt",
        "content_translate_prompt",
        "summary_prompt",
        "max_tokens",
        "base_url",
    ]


class AzureAITranslatorAdmin(BaseTranslatorAdmin):
    fields = [
        "name",
        "api_key",
        "base_url",
        "version",
        "model",
        "translate_prompt",
        "content_translate_prompt",
        "summary_prompt",
        "temperature",
        "top_p",
        "frequency_penalty",
        "presence_penalty",
        "max_tokens",
    ]
    list_display = [
        "name",
        "is_valid",
        "masked_api_key",
        "model",
        "version",
        "translate_prompt",
        "content_translate_prompt",
        "summary_prompt",
        "max_tokens",
        "base_url",
    ]


class DeepLTranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "api_key", "server_url", "proxy", "max_characters"]
    list_display = [
        "name",
        "is_valid",
        "masked_api_key",
        "server_url",
        "proxy",
        "max_characters",
    ]


class DeepLXTranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "deeplx_api", "interval", "max_characters"]
    list_display = ["name", "is_valid", "deeplx_api", "interval", "max_characters"]


# @admin.register(DeepLWebTranslator)
class DeepLWebTranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "interval", "proxy", "max_characters"]
    list_display = ["name", "is_valid", "interval", "proxy", "max_characters"]


class MicrosoftTranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "api_key", "location", "endpoint", "max_characters"]
    list_display = [
        "name",
        "is_valid",
        "masked_api_key",
        "location",
        "endpoint",
        "max_characters",
    ]


class CaiYunTranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "token", "url", "max_characters"]
    list_display = ["name", "is_valid", "masked_api_key", "url", "max_characters"]


class GeminiTranslatorAdmin(BaseTranslatorAdmin):
    fields = [
        "name",
        "api_key",
        "model",
        "translate_prompt",
        "content_translate_prompt",
        "summary_prompt",
        "temperature",
        "top_p",
        "top_k",
        "max_tokens",
        "interval",
    ]
    list_display = [
        "name",
        "is_valid",
        "masked_api_key",
        "model",
        "translate_prompt",
        "content_translate_prompt",
        "summary_prompt",
        "max_tokens",
        "interval",
    ]


class GoogleTranslateWebTranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "base_url", "interval", "proxy", "max_characters"]
    list_display = [
        "name",
        "is_valid",
        "base_url",
        "proxy",
        "interval",
        "max_characters",
    ]


class ClaudeTranslatorAdmin(BaseTranslatorAdmin):
    fields = [
        "name",
        "api_key",
        "base_url",
        "model",
        "translate_prompt",
        "content_translate_prompt",
        "summary_prompt",
        "temperature",
        "top_p",
        "top_k",
        "max_tokens",
        "proxy",
    ]
    list_display = [
        "name",
        "is_valid",
        "masked_api_key",
        "model",
        "translate_prompt",
        "content_translate_prompt",
        "summary_prompt",
        "max_tokens",
        "base_url",
    ]


class MoonshotAITranslatorAdmin(BaseTranslatorAdmin):
    fields = [
        "name",
        "api_key",
        "base_url",
        "model",
        "translate_prompt",
        "content_translate_prompt",
        "summary_prompt",
        "temperature",
        "top_p",
        "frequency_penalty",
        "presence_penalty",
        "max_tokens",
    ]
    list_display = [
        "name",
        "is_valid",
        "masked_api_key",
        "model",
        "translate_prompt",
        "content_translate_prompt",
        "summary_prompt",
        "max_tokens",
        "base_url",
    ]


class TogetherAITranslatorAdmin(BaseTranslatorAdmin):
    fields = [
        "name",
        "api_key",
        "base_url",
        "model",
        "translate_prompt",
        "content_translate_prompt",
        "summary_prompt",
        "temperature",
        "top_p",
        "frequency_penalty",
        "presence_penalty",
        "max_tokens",
    ]
    list_display = [
        "name",
        "is_valid",
        "masked_api_key",
        "model",
        "translate_prompt",
        "content_translate_prompt",
        "summary_prompt",
        "max_tokens",
        "base_url",
    ]


class OpenRouterAITranslatorAdmin(BaseTranslatorAdmin):
    fields = [
        "name",
        "api_key",
        "base_url",
        "model",
        "translate_prompt",
        "content_translate_prompt",
        "summary_prompt",
        "temperature",
        "top_p",
        "frequency_penalty",
        "presence_penalty",
        "max_tokens",
    ]
    list_display = [
        "name",
        "is_valid",
        "masked_api_key",
        "model",
        "translate_prompt",
        "content_translate_prompt",
        "summary_prompt",
        "max_tokens",
        "base_url",
    ]


class GroqTranslatorAdmin(BaseTranslatorAdmin):
    fields = [
        "name",
        "api_key",
        "base_url",
        "model",
        "translate_prompt",
        "content_translate_prompt",
        "summary_prompt",
        "temperature",
        "top_p",
        "frequency_penalty",
        "presence_penalty",
        "max_tokens",
    ]
    list_display = [
        "name",
        "is_valid",
        "masked_api_key",
        "model",
        "translate_prompt",
        "content_translate_prompt",
        "summary_prompt",
        "max_tokens",
        "base_url",
    ]

class FreeTranslatorsAdmin(BaseTranslatorAdmin):
    fields = [
        "name",
        "proxies",
        "max_characters",
    ]
    list_display = [
        "name",
        "is_valid",
        "proxies",
    ]

class DoubaoTranslatorAdmin(BaseTranslatorAdmin):
    fields = [
        "name",
        "api_key",
        "endpoint_id",
        "region",
        "translate_prompt",
        "content_translate_prompt",
        "summary_prompt",
        "max_tokens",
    ]
    list_display = [
        "name",
        "is_valid",
        "masked_api_key",
        "endpoint_id",
        "translate_prompt",
        "content_translate_prompt",
        "summary_prompt",
        "max_tokens",
    ]

class OpenlTranslatorAdmin(BaseTranslatorAdmin):
    fields = [
        "name",
        "api_key",
        "url",
        "service_name",
        "max_characters",
    ]
    list_display = [
        "name",
        "is_valid",
        "masked_api_key",
        "url",
        "max_characters",
    ]

class KagiTranslatorAdmin(BaseTranslatorAdmin):
    fields = [
        "name",
        "api_key",
        "summarization_engine",
        "summary_type",
        "translate_prompt",
        "content_translate_prompt",
    ]
    list_display = [
        "name",
        "is_valid",
        "masked_api_key",
        "summarization_engine",
        "summary_type",
        "translate_prompt",
        "content_translate_prompt",
    ]

class Translated_ContentAdmin(admin.ModelAdmin):
    fields = [
        "original_content",
        "translated_content",
        "translated_language",
        "tokens",
        "characters",
    ]
    list_display = [
        "original_content",
        "translated_language",
        "translated_content",
        "tokens",
        "characters",
    ]

    # def has_change_permission(self, request, obj=None):
    #     return False

    # def has_add_permission(self, request):
    #     return False


class TestTranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "translated_text", "max_characters", "interval"]
    list_display = ["name", "is_valid", "translated_text", "max_characters", "interval"]


core_admin_site.register(OpenAITranslator, OpenAITranslatorAdmin)
core_admin_site.register(AzureAITranslator, AzureAITranslatorAdmin)
core_admin_site.register(DeepLTranslator, DeepLTranslatorAdmin)
core_admin_site.register(DeepLWebTranslator, DeepLWebTranslatorAdmin)
core_admin_site.register(DeepLXTranslator, DeepLXTranslatorAdmin)
core_admin_site.register(MicrosoftTranslator, MicrosoftTranslatorAdmin)
core_admin_site.register(CaiYunTranslator, CaiYunTranslatorAdmin)
core_admin_site.register(GeminiTranslator, GeminiTranslatorAdmin)
core_admin_site.register(
    GoogleTranslateWebTranslator, GoogleTranslateWebTranslatorAdmin
)
core_admin_site.register(ClaudeTranslator, ClaudeTranslatorAdmin)
core_admin_site.register(MoonshotAITranslator, MoonshotAITranslatorAdmin)
core_admin_site.register(TogetherAITranslator, TogetherAITranslatorAdmin)
core_admin_site.register(OpenRouterAITranslator, OpenRouterAITranslatorAdmin)
core_admin_site.register(GroqTranslator, GroqTranslatorAdmin)
core_admin_site.register(FreeTranslators, FreeTranslatorsAdmin)
core_admin_site.register(DoubaoTranslator, DoubaoTranslatorAdmin)
core_admin_site.register(OpenlTranslator, OpenlTranslatorAdmin)
core_admin_site.register(KagiTranslator, KagiTranslatorAdmin)

if settings.DEBUG:
    core_admin_site.register(Translated_Content, Translated_ContentAdmin)
    core_admin_site.register(TestTranslator, TestTranslatorAdmin)
