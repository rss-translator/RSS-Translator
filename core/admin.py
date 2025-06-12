import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.contrib import admin
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.utils.html import format_html, mark_safe
from django.utils.translation import gettext_lazy as _
from django.urls import path, reverse
from django.db import transaction

from .models import Feed
from .custom_admin_site import core_admin_site
from .forms import FeedForm
from .actions import (
    feed_export_as_opml,
    feed_force_update,
    feed_batch_modify,
)
from utils.modelAdmin_utils import status_icon
from utils.task_manager import task_manager
from .views import import_opml
from .management.commands.update_feeds import update_single_feed

BACKGROUND_EXECUTOR = ThreadPoolExecutor(max_workers=5, thread_name_prefix="feed_updater_")

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
        "show_category",
    ]
    search_fields = ["name", "feed_url", "category__name"]
    list_filter = ["fetch_status", "translation_status","category","translate_title","translate_content","summary"]
    readonly_fields = [
        "fetch_status",
        "translation_status",
        "total_tokens",
        "total_characters",
        "last_fetch",
        "show_log",        
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
        logging.info(f"Call Feed save_model: {obj}")
        feed_url_changed = "feed_url" in form.changed_data
        target_language_changed = "target_language" in form.changed_data
        # 处理默认名称设置
        obj.name = obj.name or ("Loading" if (feed_url_changed or target_language_changed) else "Empty")
        # 无需特殊处理的情况直接保存返回
        if not (feed_url_changed or target_language_changed):
            return super().save_model(request, obj, form, change)
        
        # 需要触发任务的处理流程
        obj.fetch_status = None
        obj.translation_status = None
        
        super().save_model(request, obj, form, change)

        # 处理条目数据变更
        if target_language_changed:
            obj.entries.update(translated_content=None, translated_title=None, ai_summary=None)
        if feed_url_changed:
            obj.entries.all().delete()
        
        from functools import partial
        transaction.on_commit(
            partial(
                self._submit_feed_update_task, 
                obj.name, 
                obj.id
            )
        )

    def _submit_feed_update_task(self, feed_name, feed_id):
        task_id = task_manager.submit_task(
            f"Update Feed: {feed_name}",
            update_single_feed,
            feed_id
        )
        logging.info(f"Submitted feed update task after commit: {task_id}")

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
            status_icon(obj.translation_status), # 0
            f"/feed/rss/{obj.slug}", # 1
            "rss", # 2
            f"/feed/json/{obj.slug}", # 3
            "json", # 4
            
        )

    @admin.display(description=_("Fetch Feed"))
    def fetch_feed(self, obj): # 显示3个元素：fetch状态、原url、代理feed
        return format_html(
            "<span>{0}</span><br><a href='{1}' target='_blank'>{2}</a> | <a href='{3}' target='_blank'>{4}</a>",

            status_icon(obj.fetch_status), # 0
            obj.feed_url, # 1
            "url", # 2
            f"/feed/proxy/{obj.slug}", # 3
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
    
    @admin.display(description=_("Log"))
    def show_log(self, obj):
        return format_html(
            """
            <details>
                <summary>show</summary>
                <div style="max-height: 200px; overflow: auto;">
                    {0}
                </div>
            </details>
            """,
            mark_safe(obj.log),
        )
    
    @admin.display(description=_("Category"))
    def show_category(self, obj):
        if not obj.category:
            return ""
        return format_html(
            "<a href='{0}' target='_blank'>{1}</a><br><a href='{2}' target='_blank'>rss</a> | <a href='{3}' target='_blank'>json</a>",
            f"/feed/category/proxy/{obj.category.name}",
            obj.category.name,
            f"/feed/category/rss/{obj.category.name}",
            f"/feed/category/json/{obj.category.name}",
        )
    


core_admin_site.register(Feed, FeedAdmin)

if settings.USER_MANAGEMENT:
    core_admin_site.register(User)
    core_admin_site.register(Group)
