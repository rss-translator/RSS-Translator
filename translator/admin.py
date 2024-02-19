import logging

from django.contrib import admin
from django.conf import settings
from django.utils.html import format_html

# from .models import OpenAITranslator, DeepLTranslator, MicrosoftTranslator, AzureAITranslator, \
#    DeepLXTranslator, CaiYunTranslator, GeminiTranslator, ClaudeTranslator
from .models import *
from .tasks import translator_validate


class BaseTranslatorAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        logging.info("Call save_model: %s", obj)
        obj.valid = None
        obj.save()
        translator_validate(obj)  # 会执行一次obj.save()

    def is_valid(self, obj):
        if obj.valid is None:
            return format_html(
                "<img src='/static/img/icon-loading.svg' alt='In Progress'>"
            )
        elif obj.valid is True:
            return format_html(
                "<img src='/static/admin/img/icon-yes.svg' alt='Succeed'>"
            )
        else:
            return format_html(
                "<img src='/static/admin/img/icon-no.svg' alt='Error'>"
            )

    is_valid.short_description = 'Valid'


@admin.register(OpenAITranslator)
class OpenAITranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "api_key", "base_url", "model", "prompt", "temperature", "top_p", "frequency_penalty",
              "presence_penalty", "max_tokens"]
    list_display = ["name", "is_valid", "api_key", "model", "prompt", "max_tokens", "base_url"]


@admin.register(AzureAITranslator)
class AzureAITranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "api_key", "endpoint", "version", "deloyment_name", "prompt", "temperature", "top_p",
              "frequency_penalty", "presence_penalty", "max_tokens"]
    list_display = ["name", "is_valid", "api_key", "deloyment_name", "version", "prompt", "max_tokens", "endpoint"]


@admin.register(DeepLTranslator)
class DeepLTranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "api_key", "server_url", "proxy"]
    list_display = ["name", "is_valid", "api_key", "server_url", "proxy"]


@admin.register(DeepLXTranslator)
class DeepLXTranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "deeplx_api", "interval"]
    list_display = ["name", "is_valid", "deeplx_api", "interval"]


# @admin.register(DeepLWebTranslator)
class DeepLWebTranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "interval", "proxy"]
    list_display = ["name", "is_valid", "interval", "proxy"]

@admin.register(MicrosoftTranslator)
class MicrosoftTranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "api_key", "location", "endpoint"]
    list_display = ["name", "is_valid", "api_key", "location", "endpoint"]


@admin.register(CaiYunTranslator)
class CaiYunTranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "token", "url"]
    list_display = ["name", "is_valid", "token", "url"]


@admin.register(GeminiTranslator)
class GeminiTranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "api_key", "model", "prompt", "temperature", "top_p", "top_k", "max_tokens", "interval"]
    list_display = ["name", "is_valid", "api_key", "model", "prompt", "max_tokens", "interval"]


@admin.register(GoogleTranslateWebTranslator)
class GoogleTranslateWebTranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "base_url", "interval", "proxy"]
    list_display = ["name", "is_valid", "base_url", "proxy", "interval"]

@admin.register(ClaudeTranslator)
class ClaudeTranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "api_key", "base_url", "model", "prompt", "temperature", "top_p", "top_k", "max_tokens", "proxy"]
    list_display = ["name", "is_valid", "api_key", "model", "prompt", "max_tokens", "base_url"]


if settings.DEBUG:
    @admin.register(Translated_Content)
    class Translated_ContentAdmin(admin.ModelAdmin):
        # not permission to change anythin
        fields = ["original_content", "translated_content", "translated_language", "tokens", "characters"]
        list_display = ["original_content", "translated_language", "translated_content", "tokens", "characters"]


    @admin.register(TestTranslator)
    class TestTranslatorAdmin(BaseTranslatorAdmin):
        fields = ["name", "translated_text", "max_characters", "interval"]
        list_display = ["name", "is_valid", "translated_text", "max_characters", "interval"]
