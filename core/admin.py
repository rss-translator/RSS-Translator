import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.contrib import admin
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.utils.html import format_html, mark_safe
from django.utils.translation import gettext_lazy as _
from django.urls import path, reverse
from django.db import close_old_connections

from .models import *
from .custom_admin_site import core_admin_site
from .forms import FeedForm
from .actions import (
    feed_export_as_opml,
    feed_force_update,
    feed_batch_modify,
)
from core.management.commands.update_feeds import update_feeds_immediately
from utils.modelAdmin_utils import status_icon
from .views import import_opml

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
        "category",
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
        logging.info("Call Feed save_model: %s", obj)
        feed_url_changed = "feed_url" in form.changed_data
        translation_display_changed = "translation_display" in form.changed_data
        if feed_url_changed or translation_display_changed:
            obj.fetch_status = None
            obj.translation_status = None
            obj.name = obj.name or "Loading"
            obj.save()
            # 提交后台更新任务到线程池
            self._submit_background_update(obj.id)
        else:
            obj.name = obj.name or "Empty"
            obj.save()

    def _submit_background_update(self, feed_id):
        """提交后台更新任务到线程池"""
        # 创建任务并提交到线程池
        future = BACKGROUND_EXECUTOR.submit(self._execute_feed_update, feed_id)
        
        # 添加回调处理（可选）
        future.add_done_callback(self._handle_update_result)

    def _execute_feed_update(self, feed_id):
        """在后台线程中执行feed更新"""
        from .models import Feed
        
        try:
            # 确保在新线程中创建新的数据库连接
            close_old_connections()
            
            # 重新获取feed对象
            feed = Feed.objects.get(id=feed_id)
            logging.info(f"Starting background update for feed: {feed.name} (ID: {feed_id})")
            
            # 执行更新操作
            update_feeds_immediately([feed])
            
            logging.info(f"Completed background update for feed: {feed.name} (ID: {feed_id})")
            return True
        except Exception as e:
            logging.error(f"Background feed update failed for ID {feed_id}: {str(e)}")
            return False
        finally:
            # 确保关闭数据库连接
            close_old_connections()

    def _handle_update_result(self, future):
        """处理后台任务结果（可选）"""
        try:
            success = future.result()
            if success:
                logging.debug("Feed update completed successfully")
            else:
                logging.warning("Feed update completed with errors")
        except Exception as e:
            logging.error(f"Exception in background task: {str(e)}")

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

            status_icon(obj.fetch_status), # 0
            obj.feed_url, # 1
            "url", # 2
            f"/rss/proxy/{obj.slug}", # 3
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
        return status_icon(obj.valid)

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


class TestTranslatorAdmin(BaseTranslatorAdmin):
    fields = ["name", "translated_text", "max_characters", "interval"]
    list_display = ["name", "is_valid", "translated_text", "max_characters", "interval"]


core_admin_site.register(Feed, FeedAdmin)
core_admin_site.register(OpenAITranslator, OpenAITranslatorAdmin)
core_admin_site.register(DeepLTranslator, DeepLTranslatorAdmin)

if settings.USER_MANAGEMENT:
    core_admin_site.register(User)
    core_admin_site.register(Group)

if settings.DEBUG:
    core_admin_site.register(Translated_Content, Translated_ContentAdmin)
    core_admin_site.register(TestTranslator, TestTranslatorAdmin)
