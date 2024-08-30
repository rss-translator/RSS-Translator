import logging
from django.contrib import admin
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.urls import path, reverse

from .models import O_Feed, T_Feed
from .custom_admin_site import core_admin_site
from .forms import O_FeedForm
from .inlines import T_FeedInline
from .actions import (
    o_feed_export_as_opml,
    t_feed_export_as_opml,
    o_feed_force_update,
    t_feed_force_update,
    o_feed_batch_modify,
    t_feed_batch_modify,
)
from .tasks import update_original_feed, update_translated_feed
from utils.modelAdmin_utils import valid_icon
from .views import import_opml


class O_FeedAdmin(admin.ModelAdmin):
    form = O_FeedForm
    inlines = [T_FeedInline]
    list_display = [
        "name",
        "is_valid",
        "show_feed_url",
        "translated_language",
        "translator",
        "size_in_kb",
        "update_frequency",
        "last_pull",
        "category",
    ]
    search_fields = ["name", "feed_url", "category__name"]
    list_filter = ["valid", "category"]
    actions = [o_feed_force_update, o_feed_export_as_opml, o_feed_batch_modify]
    list_per_page = 20

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import_opml/', self.admin_site.admin_view(import_opml), name='core_o_feed_import_opml'),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['import_opml_button'] = format_html(
            '<a class="button" href="{}">导入OPML</a>',
            reverse('admin:core_o_feed_import_opml')
        )
        return super().changelist_view(request, extra_context=extra_context)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if instance.o_feed.pk:  # 不保存o_feed为空的T_Feed实例
                instance.status = None
                instance.save()
                #revoke_tasks_by_arg(instance.sid)
                update_translated_feed.schedule(args=(instance.sid,True), delay=1)

        for instance in formset.deleted_objects:
            #revoke_tasks_by_arg(instance.sid)
            instance.delete()
        formset.save_m2m()

    def save_model(self, request, obj, form, change):
        logging.info("Call O_Feed save_model: %s", obj)
        feed_url_changed = "feed_url" in form.changed_data
        # feed_name_changed = 'name' in form.changed_data
        frequency_changed = "update_frequency" in form.changed_data
        translation_display_changed = "translation_display" in form.changed_data
        # translator_changed = 'content_type' in form.changed_data or 'object_id' in form.changed_data
        if feed_url_changed or translation_display_changed:
            obj.valid = None
            obj.name = obj.name or "Loading"
            obj.save()
            update_original_feed.schedule(
                args=(obj.sid,True), delay=1
            )  # 会执行一次save() # 不放在model的save里是为了排除translator的更新，省流量
        elif frequency_changed:
            obj.save()
            #revoke_tasks_by_arg(obj.sid)
            update_original_feed.schedule(
                args=(obj.sid,), delay=obj.update_frequency * 60
            )
        else:
            obj.name = obj.name or "Empty"
            obj.save()

    @admin.display(description=_("Translator"))
    def translator(self, obj):
        return obj.translator

    @admin.display(description=_("Translated Language"))
    def translated_language(self, obj):
        return ", ".join(t_feed.language for t_feed in obj.t_feed_set.all())

    # def get_queryset(self, request):
    #     return super().get_queryset(request).prefetch_related('tags')
    # def tag_list(self, obj):
    #     return ", ".join(o.name for o in obj.tags.all())

    @admin.display(description=_("Size(KB)"), ordering="size")
    def size_in_kb(self, obj):
        return int(obj.size / 1024)

    @admin.display(description=_("Valid"), ordering="valid")
    def is_valid(self, obj):
        return valid_icon(obj.valid)

    @admin.display(description=_("Feed URL"))
    def show_feed_url(self, obj):
        if obj.feed_url:
            url = obj.feed_url
            return format_html(
                "<a href='{0}' target='_blank'>{1}...</a>",
                # "<button type='button' class='btn' data-url='{0}' onclick=''>Update</button>",
                url,
                url[:30],
            )
        return ""

    def proxy_feed_url(self, obj):
        if obj.sid:
            return format_html(
                "<a href='/rss/{0}' target='_blank'>Proxy URL</a>", obj.sid
            )
        return ""


class T_FeedAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "feed_url",
        "o_feed",
        "status_icon",
        "language",
        "translate_title",
        "translate_content",
        "summary",
        "total_tokens",
        "total_characters",
        "size_in_kb",
        "modified",
    ]
    list_filter = ["status", "translate_title", "translate_content", "o_feed__category"]
    search_fields = ["sid", "o_feed__category__name", "o_feed__feed_url"]
    readonly_fields = [
        "status",
        "language",
        "sid",
        "o_feed",
        "total_tokens",
        "total_characters",
        "size",
        "modified",
    ]
    actions = [t_feed_force_update, t_feed_export_as_opml, t_feed_batch_modify]
    list_per_page = 20
    # def get_search_results(self, request, queryset, search_term):
    #     queryset, use_distinct = super().get_search_results(request, queryset, search_term)
    #     queryset |= self.model.objects.filter(o_feed__feed_url__icontains=search_term)
    #     return queryset, use_distinct

    # def get_queryset(self, request):
    #     return super().get_queryset(request).prefetch_related('o_feed__category')

    def size_in_kb(self, obj):
        return int(obj.size / 1024)

    size_in_kb.short_description = _("Size(KB)")

    def feed_url(self, obj):
        if obj.sid:
            return format_html("<a href='/rss/{0}' target='_blank'>{0}  </a>", obj.sid)
        return ""

    feed_url.short_description = _("Translated Feed URL")

    def has_add_permission(self, request):
        return False

    def status_icon(self, obj):
        return valid_icon(obj.status)

    status_icon.short_description = _("Status")
    status_icon.admin_order_field = "status"


core_admin_site.register(O_Feed, O_FeedAdmin)
core_admin_site.register(T_Feed, T_FeedAdmin)

if settings.USER_MANAGEMENT:
    core_admin_site.register(User)
    core_admin_site.register(Group)
