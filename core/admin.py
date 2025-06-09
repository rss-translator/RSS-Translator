import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.contrib import admin
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.utils.html import format_html, mark_safe
from django.utils.translation import gettext_lazy as _
from django.urls import path, reverse
from django.db import close_old_connections
from django.shortcuts import redirect, render

from .models import *
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

@admin.register(Feed)
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

@admin.register(OpenAITranslator)
class OpenAITranslatorAdmin(TypedModelAdmin):
    pass
    # base_fields = [
    #     "name",
    #     "api_key",
    #     "base_url",
    #     "model",
    #     "translate_prompt",
    #     "content_translate_prompt",
    #     "summary_prompt",
    #     "temperature",
    #     "top_p",
    #     "frequency_penalty",
    #     "presence_penalty",
    #     "max_tokens",
    # ]
    # list_display = [
    #     "name",
    #     "is_valid",
    #     "masked_api_key",
    #     "model",
    #     "translate_prompt",
    #     "content_translate_prompt",
    #     "summary_prompt",
    #     "max_tokens",
    #     "base_url",
    # ]

@admin.register(DeepLTranslator)
class DeepLTranslatorAdmin(TypedModelAdmin):
    pass
    #base_fields = ["name", "api_key", "server_url", "proxy", "max_characters"]
    # list_display = [
    #     "name",
    #     "is_valid",
    #     "masked_api_key",
    #     "server_url",
    #     "proxy",
    #     "max_characters",
    # ]

@admin.register(TestTranslator)
class TestTranslatorAdmin(TypedModelAdmin):
    pass
    #base_fields = ["name", "translated_text", "max_characters", "interval"]
    #list_display = ["name", "is_valid", "translated_text", "max_characters", "interval"]
    
@admin.register(Translator)
class TranslatorParentAdmin(TypedModelAdmin):
    #list_display = ["name", "is_valid", "masked_api_key", "translator_type"]
    list_display = ["name", "get_translator_type"]
    list_display_links = ["name"]
    #list_filter = ["translator_type"]
    search_fields = ["name"]



    def get_translator_type(self, obj):
        """显示翻译器类型"""
        if hasattr(obj, 'polymorphic_ctype'):
            return obj.polymorphic_ctype.model.replace('translator', '').upper()
        return ""
    get_translator_type.short_description = 'Type'
    
    def get_child_model_admin(self, obj):
        """
        根据对象类型返回对应的子模型 Admin 类
        """
        if obj is None:
            return None
        for model, admin_cls in self._registry.items():
            if model == obj.get_real_instance_class():
                return admin_cls
        return None
    # def get_child_model_admin(self, obj):
    #     if isinstance(obj, OpenAITranslator):
    #         return OpenAITranslatorAdmin
    #     elif isinstance(obj, DeepLTranslator):
    #         return DeepLTranslatorAdmin
    #     elif isinstance(obj, TestTranslator):
    #         return TestTranslatorAdmin
    #     return super().get_child_model_admin(obj)

admin.site.site_header = _("RSS Translator Admin")
admin.site.site_title = _("RSS Translator")
admin.site.index_title = _("Dashboard")

if settings.USER_MANAGEMENT:
    admin.site.register(User)
    admin.site.register(Group)
else:
    admin.site.unregister(User)
    admin.site.unregister(Group)