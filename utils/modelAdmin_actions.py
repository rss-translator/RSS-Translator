import logging
from django.urls import reverse
from django.http import HttpResponse
from opyml import OPML, Outline
from huey.contrib.djhuey import HUEY as huey
from django.conf import settings
from django.db import transaction

from core.tasks import update_original_feed, update_translated_feed

if settings.DEBUG:
    from huey_monitor.models import TaskModel

class ExportMixin:
    def o_feed_export_as_opml(self, request, queryset):
        opml_obj = OPML()

        for item in queryset:
            outline = Outline(title=item.name, text=item.name, type='rss', xml_url=item.feed_url)
            opml_obj.body.outlines.append(outline)

        response = HttpResponse(opml_obj.to_xml(), content_type='application/xml')
        response['Content-Disposition'] = 'attachment; filename="rsstranslator_original_feeds.opml"'
        return response

    o_feed_export_as_opml.short_description = "Export selected original feeds as OPML"

    def t_feed_export_as_opml(self, request, queryset):
        opml_obj = OPML()

        for item in queryset:
            text = item.o_feed.name or 'No Name'
            xml_url = request.build_absolute_uri(reverse('core:rss', kwargs={'feed_sid': item.sid}))
            outline = Outline(title=text, text=text, type='rss', xml_url=xml_url)
            opml_obj.body.outlines.append(outline)

        response = HttpResponse(opml_obj.to_xml(), content_type='application/xml')
        response['Content-Disposition'] = 'attachment; filename="rsstranslator_translated_feeds.opml"'
        return response
    t_feed_export_as_opml.short_description = "Export selected translated feeds as OPML"

class ForceUpdateMixin:
    def o_feed_force_update(self, request, queryset):
        logging.info("Call o_feed_force_update: %s", queryset)
        with transaction.atomic():
            for instance in queryset:
                instance.etag = ''
                instance.valid = None
                instance.save()
                self.revoke_tasks_by_arg(instance.sid)
                update_original_feed.schedule(args=(instance.sid,), delay=1)  # 会执行一次save()
    o_feed_force_update.short_description = "Force update"

    def t_feed_force_update(self, request, queryset):
        logging.info("Call t_feed_force_update: %s", queryset)
        with transaction.atomic():
            for instance in queryset:
                instance.modified = None
                instance.status = None
                instance.save()
                self.revoke_tasks_by_arg(instance.sid)
                update_translated_feed.schedule(args=(instance.sid,), delay=1)  # 会执行一次save()
    t_feed_force_update.short_description = "Force update"

    def revoke_tasks_by_arg(self, arg_to_match):
        for task in huey.scheduled():
            # Assuming the first argument is the one we're interested in (e.g., obj.pk)
            if task.args and task.args[0] == arg_to_match:
                logging.info("Revoke task: %s", task)
                huey.revoke_by_id(task)
                # delete TaskModel data
                if settings.DEBUG:
                    TaskModel.objects.filter(task_id=task.id).delete()