import logging
from datetime import datetime
from ast import literal_eval
from opyml import OPML, Outline, Head
from django.contrib import admin
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.db import transaction
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from utils.modelAdmin_utils import get_translator_and_summary_choices
from .custom_admin_site import core_admin_site
from .models import Feed
from utils.task_manager import task_manager
from .management.commands.update_feeds import update_single_feed


@admin.display(description=_("Clean translated content"))
def clean_translated_content(modeladmin, request, queryset):
    pass

@admin.display(description=_("Export selected feeds as OPML"))
def feed_export_as_opml(modeladmin, request, queryset): # TODO
    try:
        opml_obj = OPML()
        opml_obj.head = Head(
            title="Feeds | RSS Translator",
            date_created=datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z"),
            owner_name="RSS Translator",
        )

        categories = {}
        for item in queryset:
            category = item.category.name if item.category else "default"
            # category_outline = Outline(text=category)
            if category not in categories:
                categories[category] = Outline(text=category)

            item_outline = Outline(
                title=item.name,
                text=item.name,
                type="rss",
                xml_url=item.feed_url,
                html_url=item.feed_url,
            )
            categories[category].outlines.append(item_outline)

            # category_outline.outlines.append(item_outline)
            # opml_obj.body.outlines.append(category_outline)
        for category_outline in categories.values():
            opml_obj.body.outlines.append(category_outline)

        response = HttpResponse(opml_obj.to_xml(), content_type="application/xml")
        response["Content-Disposition"] = (
            'attachment; filename="rsstranslator_feeds.opml"'
        )
        return response
    except Exception as e:
        logging.error("feed_export_as_opml: %s", str(e))
        return HttpResponse("An error occurred", status=500)


@admin.display(description=_("Force update"))
def feed_force_update(modeladmin, request, queryset):
    logging.info("Call feed_force_update: %s", queryset)
    # 清除所有选中Feed的缓存
    all_cache_keys = []
    for instance in queryset:
        # 构建缓存键 - 使用与dynamic_cache_page相同的逻辑
        cache_keys = [
            f'view_cache_rss_{instance.slug}_t',
            f'view_cache_rss_{instance.slug}_o',
            f'view_cache_rss_json_{instance.slug}_t',
            f'view_cache_rss_json_{instance.slug}_o',
            f'view_cache_proxy_{instance.slug}_t',
            f'view_cache_proxy_{instance.slug}_o',
        ]
        all_cache_keys.extend(cache_keys)

    if all_cache_keys:
        cache.delete_many(all_cache_keys)

    with transaction.atomic():
        for instance in queryset:
            instance.fetch_status = None
            instance.translation_status = None
            instance.save()
    
    for feed_id in queryset.values_list("id", flat=True):
        task_manager.submit_task(
            f"Force Update Feed: {feed_id}",
            update_single_feed,
            feed_id
        )


@admin.display(description=_("Batch modification"))
def feed_batch_modify(modeladmin, request, queryset):
    if "apply" in request.POST:
        logging.info("Apply feed_batch_modify")
        post_data = request.POST
        fields = {
            "update_frequency": "update_frequency_value",
            "max_posts": "max_posts_value",
            "translator": "translator_value",
            "target_language": "target_language_value",
            "translation_display": "translation_display_value",
            "summarizer": "summarizer_value",
            "summary_detail": "summary_detail_value",
            "additional_prompt": "additional_prompt_value",
            "fetch_article": "fetch_article",
            "quality": "quality",
            "category": "category_value",
            "translate_title": "translate_title",
            "translate_content": "translate_content",
            "summary": "summary",
        }
        field_types = {
            "update_frequency": int,
            "max_posts": int,
            "target_language": str,
            "translation_display": int,
            "summary_detail": float,
            "additional_prompt": str,
            "fetch_article": literal_eval,
            "quality": literal_eval,
            "translate_title": literal_eval,
            "translate_content": literal_eval,
            "summary": literal_eval,
        }
        translate_title = request.POST.get("translate_title", "Keep")
        translate_content = request.POST.get("translate_content", "Keep")
        summary = request.POST.get("summary", "Keep")

        match translate_title:
            case "Keep":
                pass
            case "True":
                queryset.update(translate_title=True)
            case "False":
                queryset.update(translate_title=False)

        match translate_content:
            case "Keep":
                pass
            case "True":
                queryset.update(translate_content=True)
            case "False":
                queryset.update(translate_content=False)

        match summary:
            case "Keep":
                pass
            case "True":
                queryset.update(summary=True)
            case "False":
                queryset.update(summary=False)

        update_fields = {}
        for field, value_field in fields.items():
            value = post_data.get(value_field)
            if post_data.get(field, "Keep") != "Keep" and value:
                match field:
                    case "translator":
                        content_type_id, object_id = map(int, value.split(":"))
                        queryset.update(translator_content_type_id=content_type_id)
                        queryset.update(translator_object_id=object_id)
                    case "summarizer":
                        content_type_summary_id, object_id_summary = map(
                            int, value.split(":")
                        )
                        queryset.update(summarizer_content_type_id=content_type_summary_id)
                        queryset.update(summarizer_object_id=object_id_summary)
                    case "category":
                        tag_model = Feed.category.tag_model
                        category_o, _ = tag_model.objects.get_or_create(name=value)
                        queryset.update(category=category_o)

                    case _:
                        update_fields[field] = field_types.get(field, str)(value)

        if update_fields:
            queryset.update(**update_fields)
        return redirect(request.get_full_path())

    translator_choices, summary_engine_choices = get_translator_and_summary_choices()
    logging.info(
        "translator_choices: %s, summary_engine_choices: %s",
        translator_choices,
        summary_engine_choices,
    )
    return render(
        request,
        "admin/feed_batch_modify.html",
        context={
            **core_admin_site.each_context(request),
            "items": queryset,
            "translator_choices": translator_choices,
            "target_language_choices": settings.TRANSLATION_LANGUAGES,
            "summary_engine_choices": summary_engine_choices,
            "update_frequency_choices": [
                (5, "5 min"),
                (15, "15 min"),
                (30, "30 min"),
                (60, "hourly"),
                (1440, "daily"),
                (10080, "weekly"),
            ],
        },
    )