import logging

from django.contrib import admin
from django.conf import settings

from .models import Translated_Content, OpenAITranslator, DeepLTranslator, MicrosoftTranslator, AzureAITranslator, \
    DeepLXTranslator
from .tasks import translator_validate

@admin.register(OpenAITranslator)
class OpenAITranslatorAdmin(admin.ModelAdmin):
    fields = ["name", "api_key", "base_url", "model", "prompt", "temperature", "top_p","frequency_penalty","presence_penalty","max_tokens"]
    list_display = ["name", "valid", "api_key", "model", "prompt", "max_tokens","base_url"]

    def save_model(self, request, obj, form, change):
        logging.debug("Call save_model: %s", obj)
        obj.valid = None
        obj.save()
        translator_validate(obj)  # 会执行一次obj.save()


@admin.register(AzureAITranslator)
class AzureAITranslatorAdmin(admin.ModelAdmin):
    fields = ["name", "api_key", "endpoint", "version","deloyment_name", "prompt", "temperature", "top_p","frequency_penalty","presence_penalty","max_tokens"]
    list_display = ["name", "valid", "api_key", "deloyment_name", "version", "prompt", "max_tokens","endpoint"]

    def save_model(self, request, obj, form, change):
        logging.debug("Call save_model: %s", obj)
        obj.valid = None
        obj.save()
        translator_validate(obj)  # 会执行一次obj.save()

@admin.register(DeepLTranslator)
class DeepLTranslatorAdmin(admin.ModelAdmin):
    fields = ["name", "api_key"]
    list_display = ["name", "valid", "api_key"]

    def save_model(self, request, obj, form, change):
        logging.debug("Call save_model: %s", obj)
        obj.valid = None
        obj.save()
        translator_validate(obj)  # 会执行一次obj.save()


@admin.register(DeepLXTranslator)
class DeepLXTranslatorAdmin(admin.ModelAdmin):
    fields = ["name", "deeplx_api"]
    list_display = ["name", "valid", "deeplx_api"]

    def save_model(self, request, obj, form, change):
        logging.debug("Call save_model: %s", obj)
        obj.valid = None
        obj.save()
        translator_validate(obj)  # 会执行一次obj.save()


@admin.register(MicrosoftTranslator)
class MicrosoftTranslatorAdmin(admin.ModelAdmin):
    fields = ["name", "api_key", "location", "endpoint"]
    list_display = ["name", "valid", "api_key", "location", "endpoint"]

    def save_model(self, request, obj, form, change):
        logging.debug("Call save_model: %s", obj)
        obj.valid = None
        obj.save()
        translator_validate(obj)  # 会执行一次obj.save()


class Translated_ContentAdmin(admin.ModelAdmin):
    # not permission to change anythin
    fields = ["original_content", "translated_content", "translated_language", "tokens", "characters"]
    list_display = ["original_content", "translated_language", "translated_content", "tokens", "characters"]


if settings.DEBUG:
    admin.site.register(Translated_Content, Translated_ContentAdmin)
