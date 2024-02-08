import logging

from django import forms
from django.contrib import admin
from django.conf import settings
from django.db import transaction

if settings.DEBUG:
    from huey_monitor.models import TaskModel

from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy  as _

from huey.contrib.djhuey import HUEY as huey
from translator.models import TestTranslator, OpenAITranslator, DeepLTranslator, MicrosoftTranslator, AzureAITranslator, \
    DeepLXTranslator, CaiYunTranslator

from .models import O_Feed, T_Feed
from .tasks import update_original_feed, update_translated_feed

admin.site.site_header = _('RSS Translator Admin')
admin.site.site_title = _('RSS Translator')
admin.site.index_title = _('Dashboard')


class T_FeedForm(forms.ModelForm):
    class Meta:
        model = T_Feed
        fields = ['language', 'translate_title']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['language'].disabled = True
class T_FeedInline(admin.TabularInline):
    model = T_Feed
    form = T_FeedForm
    fields = ["language", "obj_status", "feed_url", "translate_title", "translate_content", "total_tokens",
              "total_characters", "size_in_kb"]
    readonly_fields = ("feed_url", "obj_status", "size_in_kb", "total_tokens", "total_characters")
    extra = 1

    def feed_url(self, obj):
        if obj.sid:
            url = reverse('core:rss', kwargs={'feed_sid': obj.sid})
            full_url = self.request.build_absolute_uri(url)
            return format_html(
                "<a href='{0}' target='_blank'>{0}  </a>"
                "<button type='button' class='btn' data-url='{0}' onclick='copyToClipboard(this)'>Copy</button>",
                full_url
            )
        return ''

    feed_url.short_description = _('Feed URL')

    class Media:
        js = ('js/admin/copytoclipboard.js',)

    def size_in_kb(self, obj):
        return int(obj.size / 1024)

    size_in_kb.short_description = 'Size(KB)'

    def obj_status(self, obj):
        if not obj.pk:
            return ''
        if obj.status is None:
            return format_html(
                "<img src='/static/img/icon-loading.svg' alt='In Progress'>"
            )
        elif obj.status is True:
            return format_html(
                "<img src='/static/admin/img/icon-yes.svg' alt='Succeed'>"
            )
        else:
            return format_html(
                "<img src='/static/admin/img/icon-no.svg' alt='Error'>"
            )

    obj_status.short_description = 'Status'
    def get_formset(self, request, obj=None, **kwargs):
        # Store the request for use in feed_url
        self.request = request
        return super(T_FeedInline, self).get_formset(request, obj, **kwargs)


class O_FeedForm(forms.ModelForm):
    # 自定义字段，使用ChoiceField生成下拉菜单
    translator_engine = forms.ChoiceField(choices=(), required=False)

    def __init__(self, *args, **kwargs):
        super(O_FeedForm, self).__init__(*args, **kwargs)
        translator_models = [TestTranslator, OpenAITranslator, DeepLTranslator, MicrosoftTranslator, AzureAITranslator,
                             DeepLXTranslator, CaiYunTranslator]
        # Cache ContentTypes to avoid repetitive database calls
        content_types = {model: ContentType.objects.get_for_model(model) for model in translator_models}

        # Build all choices in one list comprehension
        translator_choices = [
            (f"{content_types[model].id}:{obj_id}", obj_name)
            for model in translator_models
            for obj_id, obj_name in model.objects.filter(valid=True).values_list('id', 'name')
        ]
        self.fields['translator_engine'].choices = translator_choices

        # 如果已经有关联的对象，设置默认值
        instance = getattr(self, 'instance', None)
        if instance and instance.pk and instance.content_type and instance.object_id:
            self.fields['translator_engine'].initial = f"{instance.content_type.id}:{instance.object_id}"

    class Meta:
        model = O_Feed
        fields = ['feed_url', 'translator_engine', 'update_frequency']

    # 重写save方法，以处理自定义字段的数据
    def save(self, commit=True):
        # 获取选择的translator，并设置content_type和translator_object_id
        if self.cleaned_data['translator_engine']:
            content_type_id, object_id = map(int, self.cleaned_data['translator_engine'].split(':'))
            self.instance.content_type_id = content_type_id
            self.instance.object_id = object_id
        else:
            self.instance.content_type = None
            self.instance.object_id = None
        return super(O_FeedForm, self).save(commit=commit)


@admin.register(O_Feed)
class O_FeedAdmin(admin.ModelAdmin):
    form = O_FeedForm
    # fields = ['feed_url', 'content_type','object_id']
    inlines = [T_FeedInline]
    list_display = ["name", "is_valid", "show_feed_url", "translated_language", "translator", "size_in_kb",
                    "update_frequency", "modified"]
    search_fields = ["name", "feed_url"]
    actions = ['force_update']

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if instance.o_feed.pk:  # 不保存o_feed为空的T_Feed实例
                instance.status = None
                instance.save()
                self.revoke_tasks_by_arg(instance.sid)
                update_translated_feed(instance.sid, force=True)

        for instance in formset.deleted_objects:
            self.revoke_tasks_by_arg(instance.sid)
            instance.delete()
        formset.save_m2m()

    def save_model(self, request, obj, form, change):
        logging.info("Call O_Feed save_model: %s", obj)
        feed_url_changed = 'feed_url' in form.changed_data
        frequency_changed = 'update_frequency' in form.changed_data
        # translator_changed = 'content_type' in form.changed_data or 'object_id' in form.changed_data
        if feed_url_changed:
            obj.valid = None
            obj.save()
            update_original_feed(obj.sid)  # 会执行一次save() # 不放在model的save里是为了排除translator的更新，省流量
        elif frequency_changed:
            obj.save()
            self.revoke_tasks_by_arg(obj.sid)
            update_original_feed.schedule(args=(obj.sid,), delay=obj.update_frequency * 60)
        else:
            obj.save()

    def revoke_tasks_by_arg(self, arg_to_match):
        for task in huey.scheduled():
            # Assuming the first argument is the one we're interested in (e.g., obj.pk)
            if task.args and task.args[0] == arg_to_match:
                logging.info("Revoke task: %s", task)
                huey.revoke_by_id(task)
                # delete TaskModel data
                if settings.DEBUG:
                    TaskModel.objects.filter(task_id=task.id).delete()

    def translated_language(self, obj):
        return ", ".join(t_feed.language for t_feed in obj.t_feed_set.all())

    def size_in_kb(self, obj):
        return int(obj.size / 1024)

    size_in_kb.short_description = 'Size(KB)'

    def is_valid(self, obj):
        if obj.valid is None:
            return format_html(
                "<img src='/static/img/icon-loading.svg' alt='In Progress'>"
            )
        elif obj.valid is True:
            return format_html(
                "<img src='/static/admin/img/icon-yes.svg' alt='Succeed'>"
            )
        else:
            return format_html(
                "<img src='/static/admin/img/icon-no.svg' alt='Error'>"
            )

    is_valid.short_description = 'Valid'
    @admin.display(description="feed_url")
    def show_feed_url(self, obj):
        if obj.feed_url:
            return format_html(
                "<a href='{0}' target='_blank'>{0}  </a>",
                # "<button type='button' class='btn' data-url='{0}' onclick=''>Update</button>",
                obj.feed_url
            )
        return ''
    def proxy_feed_url(self, obj):
        if obj.sid:
            return format_html(
                "<a href='/rss/{0}' target='_blank'>Proxy URL</a>",
                obj.sid
            )
        return ''
    @admin.action(description=_('Force Update'))
    def force_update(self, request, queryset):
        logging.info("Call force_update: %s", queryset)
        with transaction.atomic():
            for instance in queryset:
                instance.etag = ''
                instance.modified = ''
                instance.valid = None
                instance.save()
                self.revoke_tasks_by_arg(instance.sid)
                update_original_feed.schedule(args=(instance.sid,), delay=1)  # 会执行一次save()


class T_FeedAdmin(admin.ModelAdmin):
    list_display = ["o_feed", "language", "total_tokens", "total_characters", "modified", "size_in_kb", "sid"]
    list_filter = ["o_feed", "language", "total_tokens", "total_characters", "size"]
    search_fields = ["o_feed", "language"]
    readonly_fields = ["o_feed", "total_tokens", "total_characters", "modified", "size"]

    def size_in_kb(self, obj):
        return int(obj.size / 1024)

    size_in_kb.short_description = 'Size(KB)'

if not settings.MULTIPLE_USERS:
    admin.site.unregister(User)
    admin.site.unregister(Group)

#if in debug, then register debug_toolbar
if settings.DEBUG:
    admin.site.register(T_Feed)