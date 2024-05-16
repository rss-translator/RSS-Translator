import logging
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponse
from django.utils.html import format_html
from django.apps import apps


from opyml import OPML, Outline
from huey.contrib.djhuey import HUEY as huey
#from django.conf import settings
from django.utils.translation import gettext_lazy  as _
from django.db import transaction
from django.contrib.contenttypes.models import ContentType


from core.tasks import update_original_feed, update_translated_feed

#if settings.DEBUG:
#    from huey_monitor.models import TaskModel

class CustomModelActions:
    def o_feed_export_as_opml(self, request, queryset):
        opml_obj = OPML()

        for item in queryset:
            tag_outline = Outline(text=item.tags)
            item_outline = Outline(title=item.name, text=item.name, type='rss', xml_url=item.feed_url)
            tag_outline.outlines.append(item_outline)
            opml_obj.body.outlines.append(tag_outline)

        response = HttpResponse(opml_obj.to_xml(), content_type='application/xml')
        response['Content-Disposition'] = 'attachment; filename="rsstranslator_original_feeds.opml"'
        return response

    o_feed_export_as_opml.short_description = _("Export selected feeds as OPML")

    def t_feed_export_as_opml(self, request, queryset):
        opml_obj = OPML()

        for item in queryset:
            text = item.o_feed.name or 'No Name'
            xml_url = request.build_absolute_uri(reverse('core:rss', kwargs={'feed_sid': item.sid}))

            tag_outline = Outline(text=item.o_feed.tags)
            item_outline = Outline(title=text, text=text, type='rss', xml_url=xml_url)
            tag_outline.outlines.append(item_outline)
            opml_obj.body.outlines.append(tag_outline)

        response = HttpResponse(opml_obj.to_xml(), content_type='application/xml')
        response['Content-Disposition'] = 'attachment; filename="rsstranslator_translated_feeds.opml"'
        return response
    t_feed_export_as_opml.short_description = _("Export selected feeds as OPML")

    def o_feed_force_update(self, request, queryset):
        logging.info("Call o_feed_force_update: %s", queryset)
        with transaction.atomic():
            for instance in queryset:
                instance.etag = ''
                instance.valid = None
                instance.save()
                self.revoke_tasks_by_arg(instance.sid)
                update_original_feed.schedule(args=(instance.sid,), delay=1)  # 会执行一次save()
    o_feed_force_update.short_description = _("Force update")

    def t_feed_force_update(self, request, queryset):
        logging.info("Call t_feed_force_update: %s", queryset)
        with transaction.atomic():
            for instance in queryset:
                instance.modified = None
                instance.status = None
                instance.save()
                self.revoke_tasks_by_arg(instance.sid)
                update_translated_feed.schedule(args=(instance.sid,), delay=1)  # 会执行一次save()
    t_feed_force_update.short_description = _("Force update")

    def revoke_tasks_by_arg(self, arg_to_match):
        for task in huey.scheduled():
            # Assuming the first argument is the one we're interested in (e.g., obj.pk)
            if task.args and task.args[0] == arg_to_match:
                logging.info("Revoke task: %s", task)
                huey.revoke_by_id(task)
                # delete TaskModel data
                # if settings.DEBUG:
                #     TaskModel.objects.filter(task_id=task.id).delete()


# def get_all_subclasses(cls):
#     subclasses = set()
#     for subclass in cls.__subclasses__():
#         if not subclass.__subclasses__():
#             subclasses.add(subclass)
#         subclasses.update(get_all_subclasses(subclass))
#     return subclasses
def get_all_app_models(app_name):
    app = apps.get_app_config(app_name)
    models = app.get_models()
    #exclude Translated_Content
    exclude_models = ['Translated_Content']
    if not settings.DEBUG:
        exclude_models.append('TestTranslator')

    models = [model for model in models if model.__name__ not in exclude_models]

    return models

def get_translator_and_summary_choices():
    translator_models = get_all_app_models('translator')
    # Cache ContentTypes to avoid repetitive database calls
    content_types = {model: ContentType.objects.get_for_model(model) for model in translator_models}

    # Build all choices in one list comprehension
    translator_choices = [
        (f"{content_types[model].id}:{obj_id}", obj_name)
        for model in translator_models
        for obj_id, obj_name in model.objects.filter(valid=True).values_list('id', 'name')
    ]

    summary_engine_choices = [
            (f"{content_types[model].id}:{obj_id}", obj_name)
            for model in translator_models
            for obj_id, obj_name in model.objects.filter(valid=True, is_ai=True).values_list('id', 'name')
        ]
    return translator_choices, summary_engine_choices

def valid_icon(status):
    match status:
        case None:
            return format_html("<img src='/static/img/icon-loading.svg' alt='In Progress'>")
        case True:
            return format_html("<img src='/static/admin/img/icon-yes.svg' alt='Succeed'>")
        case False:
            return format_html("<img src='/static/admin/img/icon-no.svg' alt='Error'>")

