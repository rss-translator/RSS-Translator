import logging
from datetime import datetime
from ast import literal_eval
from opyml import OPML, Outline, Head
from huey.contrib.djhuey import HUEY as huey

from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import HttpResponse
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from utils.modelAdmin_utils import get_translator_and_summary_choices
from .custom_admin_site import core_admin_site
from .models import O_Feed
from .tasks import update_original_feed, update_translated_feed


@admin.display(description=_("Export selected feeds as OPML"))
def o_feed_export_as_opml(modeladmin, request, queryset):
    try:
        opml_obj = OPML()
        opml_obj.head = Head(
            title="Original Feeds | RSS Translator",
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
            'attachment; filename="rsstranslator_original_feeds.opml"'
        )
        return response
    except Exception as e:
        logging.error("o_feed_export_as_opml: %s", str(e))
        return HttpResponse("An error occurred", status=500)


@admin.display(description=_("Export selected feeds as OPML"))
def t_feed_export_as_opml(modeladmin, request, queryset):
    try:
        opml_obj = OPML()
        opml_obj.head = Head(
            title="Translated Feeds | RSS Translator",
            date_created=datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z"),
            owner_name="RSS Translator",
        )

        categories = {}
        for item in queryset:
            category = item.o_feed.category.name if item.o_feed.category else "default"
            text = item.o_feed.name or "No Name"
            xml_url = request.build_absolute_uri(
                reverse("core:rss", kwargs={"feed_sid": item.sid})
            )

            if category not in categories:
                categories[category] = Outline(text=category)

            item_outline = Outline(
                title=text,
                text=text,
                type="rss",
                xml_url=xml_url,
                html_url=item.o_feed.feed_url,
            )
            categories[category].outlines.append(item_outline)
        for category_outline in categories.values():
            opml_obj.body.outlines.append(category_outline)

        response = HttpResponse(opml_obj.to_xml(), content_type="application/xml")
        response["Content-Disposition"] = (
            'attachment; filename="rsstranslator_translated_feeds.opml"'
        )
        return response
    except Exception as e:
        logging.error("t_feed_export_as_opml: %s", str(e))
        return HttpResponse("An error occurred", status=500)


@admin.display(description=_("Force update"))
def o_feed_force_update(modeladmin, request, queryset):
    logging.info("Call o_feed_force_update: %s", queryset)
    with transaction.atomic():
        for instance in queryset:
            instance.etag = ""
            instance.valid = None
            instance.save()
            #logging.info("Call revoke_tasks_by_arg in o_feed_force_update")
            #revoke_tasks_by_arg(instance.sid)
            update_original_feed.schedule(
                args=(instance.sid,True), delay=1,
            )  # 会执行一次save()


@admin.display(description=_("Force update"))
def t_feed_force_update(modeladmin, request, queryset):
    logging.info("Call t_feed_force_update: %s", queryset)
    with transaction.atomic():
        for instance in queryset:
            instance.modified = None
            instance.status = None
            instance.save()
            #logging.info("Call revoke_tasks_by_arg in o_feed_force_update")
            #revoke_tasks_by_arg(instance.sid) #will check in update_translated_feed task
            update_translated_feed.schedule(
                args=(instance.sid,True), delay=1
            )  # 会执行一次save()


@admin.display(description=_("Batch modification"))
def o_feed_batch_modify(modeladmin, request, queryset):
    if "apply" in request.POST:
        logging.info("Apply o_feed_batch_modify")
        post_data = request.POST
        fields = {
            "update_frequency": "update_frequency_value",
            "max_posts": "max_posts_value",
            "translator": "translator_value",
            "translation_display": "translation_display_value",
            "summary_engine": "summary_engine_value",
            "summary_detail": "summary_detail_value",
            "additional_prompt": "additional_prompt_value",
            "fetch_article": "fetch_article",
            "quality": "quality",
            "category": "category_value",
        }
        field_types = {
            "update_frequency": int,
            "max_posts": int,
            "translation_display": int,
            "summary_detail": float,
            "additional_prompt": str,
            "fetch_article": literal_eval,
            "quality": literal_eval,
        }
        update_fields = {}
        # tags_value = None

        for field, value_field in fields.items():
            value = post_data.get(value_field)
            if post_data.get(field, "Keep") != "Keep" and value:
                match field:
                    case "translator":
                        content_type_id, object_id = map(int, value.split(":"))
                        update_fields["content_type_id"] = content_type_id
                        update_fields["object_id"] = object_id
                    case "summary_engine":
                        content_type_summary_id, object_id_summary = map(
                            int, value.split(":")
                        )
                        update_fields["content_type_summary_id"] = (
                            content_type_summary_id
                        )
                        update_fields["object_id_summary"] = object_id_summary
                    case "category":
                        tag_model = O_Feed.category.tag_model
                        category_o, _ = tag_model.objects.get_or_create(name=value)
                        update_fields["category"] = category_o

                    case _:
                        update_fields[field] = field_types.get(field, str)(value)

        if update_fields:
            queryset.update(**update_fields)
        # for obj in queryset:
        #     obj.category.update_count()

        # if tags_value is not None:
        #     for obj in queryset:
        #         obj.tags = [*tags_value]
        #         obj.save()
        # O_Feed.objects.bulk_update(queryset, ['tags'])??

        # self.message_user(request, f"Successfully modified {queryset.count()} items.")
        # return HttpResponseRedirect(request.get_full_path())
        return redirect(request.get_full_path())

    translator_choices, summary_engine_choices = get_translator_and_summary_choices()
    logging.info(
        "translator_choices: %s, summary_engine_choices: %s",
        translator_choices,
        summary_engine_choices,
    )
    return render(
        request,
        "admin/o_feed_batch_modify.html",
        context={
            **core_admin_site.each_context(request),
            "items": queryset,
            "translator_choices": translator_choices,
            "summary_engine_choices": summary_engine_choices,
        },
    )


@admin.display(description=_("Batch modification"))
def t_feed_batch_modify(modeladmin, request, queryset):
    if "apply" in request.POST:
        logging.info("Apply t_feed_batch_modify")
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

        # self.message_user(request, f"Successfully modified {queryset.count()} items.")
        # return HttpResponseRedirect(request.get_full_path())
        return redirect(request.get_full_path())
    return render(
        request,
        "admin/t_feed_batch_modify.html",
        context={**core_admin_site.each_context(request), "items": queryset},
    )
