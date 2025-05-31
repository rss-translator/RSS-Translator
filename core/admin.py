import logging
from django.contrib import admin
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.urls import path, reverse

from .models import Feed
from .custom_admin_site import core_admin_site
from .forms import FeedForm
from .actions import (
    feed_export_as_opml,
    feed_force_update,
    feed_batch_modify,
)
from .tasks import update_original_feed, update_translated_feed
from utils.modelAdmin_utils import valid_icon
from .views import import_opml


class FeedAdmin(admin.ModelAdmin):
    form = FeedForm
    list_display = [
        "name",
        "fetch_feed",
        "translated_feed",
        "translator",
        "target_language",
        "translation_options",
        "simple_update_frequency",
        "last_fetch",
        "total_tokens",
        "total_characters",
        "category",
        "size_in_kb"
    ]
    search_fields = ["name", "feed_url", "category__name"]
    list_filter = ["fetch_status", "translation_status","category","translate_title","translate_content","summary"]
    readonly_fields = [
        "fetch_status",
        "translation_status",
        "total_tokens",
        "total_characters",
        "size_in_kb",
        "last_fetch",
        "log",        
    ]
    actions = [feed_force_update, feed_export_as_opml, feed_batch_modify]
    list_per_page = 20

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import_opml/', self.admin_site.admin_view(import_opml), name='core_feed_import_opml'),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['import_opml_button'] = format_html(
            '<a class="button" href="{}">导入OPML</a>',
            reverse('admin:core_feed_import_opml')
        )
        return super().changelist_view(request, extra_context=extra_context)

    def save_model(self, request, obj, form, change):
        logging.info("Call Feed save_model: %s", obj)
        feed_url_changed = "feed_url" in form.changed_data
        # feed_name_changed = 'name' in form.changed_data
        frequency_changed = "update_frequency" in form.changed_data
        translation_display_changed = "translation_display" in form.changed_data
        # translator_changed = 'content_type' in form.changed_data or 'object_id' in form.changed_data
        if feed_url_changed or translation_display_changed:
            obj.fetch_status = None
            obj.name = obj.name or "Loading"
            obj.save()
            update_original_feed.schedule(
                args=(obj.id,True), delay=1
            )  # 会执行一次save() # 不放在model的save里是为了排除translator的更新，省流量
        elif frequency_changed:
            obj.save()
            #revoke_tasks_by_arg(obj.id)
            update_original_feed.schedule(
                args=(obj.id,), delay=obj.update_frequency * 60
            )
        else:
            obj.name = obj.name or "Empty"
            obj.save()


    @admin.display(description=_("Size(KB)"), ordering="size")
    def size_in_kb(self, obj):
        return int(obj.size / 1024)
    
    @admin.display(description=_("Update Frequency"), ordering="update_frequency")
    def simple_update_frequency(self, obj):
        if obj.update_frequency <= 5:
            return "5 min"
        elif obj.update_frequency <= 15:
            return "15 min"
        elif obj.update_frequency <= 30:
            return "30 min"
        elif obj.update_frequency <= 60:
            return "hourly"
        elif obj.update_frequency <= 1440:
            return "daily"
        elif obj.update_frequency <= 10080:
            return "weekly"

    @admin.display(description=_("Translator"))
    def translator(self, obj):
        return obj.translator
    
    @admin.display(description=_("Translated Feed"))
    def translated_feed(self, obj): # 显示3个元素：translated_status、feed_url、json_url
        return format_html(
            "<span>{0}</span><br><a href='{1}' target='_blank'>{2}</a> | <a href='{3}' target='_blank'>{4}</a>",
            valid_icon(obj.translation_status), # 0
            f"/rss/{obj.slug}", # 1
            "rss", # 2
            f"/json/{obj.slug}", # 3
            "json", # 4
            
        )

    @admin.display(description=_("Fetch Feed"))
    def fetch_feed(self, obj): # 显示3个元素：fetch状态、原url、代理feed
        return format_html(
            # "<span>{0}</span> | <a href='{1}' target='_blank'>{2}</a> | <a href='{3}' target='_blank'>{4}</a>",
            "<span>{0}</span><br><a href='{1}' target='_blank'>{2}</a> | <a href='{3}' target='_blank'>{4}</a>",

            valid_icon(obj.fetch_status), # 0
            obj.feed_url, # 1
            "url", # 2
            f"/proxy/{obj.slug}", # 3
            "proxy", # 4
        )
    
    @admin.display(description=_("Options"))
    def translation_options(self, obj):
        translate_title = "🟢" if obj.translate_title else "⚪"
        translate_content = "🟢" if obj.translate_content else "⚪"
        summary_check = "🟢" if obj.summary else "⚪"
        title = _("Title")
        content = _("Content")
        summary = _("Summary")

        return format_html(
            "<span>{0}{1}</span><br><span>{2}{3}</span><br><span>{4}{5}</span>",
            translate_title,title,
            translate_content,content,
            summary_check,summary,
        )


core_admin_site.register(Feed, FeedAdmin)

if settings.USER_MANAGEMENT:
    core_admin_site.register(User)
    core_admin_site.register(Group)
