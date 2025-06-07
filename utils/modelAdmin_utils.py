from django.conf import settings
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from core.models import DeepLTranslator, OpenAITranslator, TestTranslator

def get_translator_models():
    translator_models = [DeepLTranslator, OpenAITranslator]
    # exclude Translated_Content
    if not settings.DEBUG:
        translator_models.append(TestTranslator)

    return translator_models


def get_translator_and_summary_choices():
    translator_models = get_translator_models()
    
    # Cache ContentTypes to avoid repetitive database calls
    content_types = {
        model: ContentType.objects.get_for_model(model) for model in translator_models
    }

    # Build all choices in one list comprehension
    translator_choices = [
        (f"{content_types[model].id}:{obj_id}", obj_name)
        for model in translator_models
        for obj_id, obj_name in model.objects.filter(valid=True).values_list(
            "id", "name"
        )
    ]

    summary_engine_choices = [
        (f"{content_types[model].id}:{obj_id}", obj_name)
        for model in translator_models
        for obj_id, obj_name in model.objects.filter(
            valid=True, is_ai=True
        ).values_list("id", "name")
    ]
    return translator_choices, summary_engine_choices

def status_icon(status):
    match status:
        case None:
            return format_html(
                "<img src='/static/img/icon-loading.svg' alt='In Progress'>"
            )
        case True:
            return format_html(
                "<img src='/static/admin/img/icon-yes.svg' alt='Succeed'>"
            )
        case False:
            return format_html("<img src='/static/admin/img/icon-no.svg' alt='Error'>")
