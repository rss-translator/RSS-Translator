import logging

from django import forms
from django.contrib import admin
from django.conf import settings

from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy  as _

from django_text_translator.models import TranslatorEngine

from .models import O_Feed, T_Feed
from .tasks import update_original_feed, update_translated_feed
from utils.modelAdmin_actions import ExportMixin, ForceUpdateMixin

admin.site.site_header = _('RSS Translator Admin')
admin.site.site_title = _('RSS Translator')
admin.site.index_title = _('Dashboard')


class T_FeedForm(forms.ModelForm):
    class Meta:
        model = T_Feed
        fields = ['language', 'translate_title','sid']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sid'].required = False
        if self.instance.pk:
            self.fields['language'].disabled = True
            self.fields['sid'].disabled = True

class T_FeedInline(admin.TabularInline):
    model = T_Feed
    form = T_FeedForm
    fields = ["language", "obj_status", "feed_url", "translate_title", "translate_content", "total_tokens",
              "total_characters", "size_in_kb",'sid']
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
        translator_models = TranslatorEngine.__subclasses__()
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
        fields = ['feed_url', 'update_frequency', 'max_posts', 'translator_engine', 'name']

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
class O_FeedAdmin(admin.ModelAdmin, ExportMixin, ForceUpdateMixin):
    form = O_FeedForm
    inlines = [T_FeedInline]
    list_display = ["name", "is_valid", "show_feed_url", "translated_language", "translator", "size_in_kb",
                    "update_frequency", "last_updated", "last_pull"]
    search_fields = ["name", "feed_url"]
    list_filter = ["valid"]
    actions = ['o_feed_force_update', 'o_feed_export_as_opml']

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
        feed_name_changed = 'name' in form.changed_data
        frequency_changed = 'update_frequency' in form.changed_data
        # translator_changed = 'content_type' in form.changed_data or 'object_id' in form.changed_data
        if feed_url_changed:
            obj.valid = None
            obj.name = "Loading" if not obj.name else obj.name
            obj.save()
            update_original_feed(obj.sid)  # 会执行一次save() # 不放在model的save里是为了排除translator的更新，省流量
        elif frequency_changed:
            obj.save()
            self.revoke_tasks_by_arg(obj.sid)
            update_original_feed.schedule(args=(obj.sid,), delay=obj.update_frequency * 60)
        else:
            obj.name = "Empty" if not obj.name else obj.name
            obj.save()

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
    is_valid.admin_order_field = 'valid'
    size_in_kb.admin_order_field = 'size'

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

@admin.register(T_Feed)
class T_FeedAdmin(admin.ModelAdmin, ExportMixin, ForceUpdateMixin):
    list_display = ["id", "feed_url", "o_feed", "status_icon", "language", "translate_title", "translate_content", "total_tokens", "total_characters", "size_in_kb", "modified"]
    list_filter = ["status", "translate_title", "translate_content"]
    search_fields = ["sid"]
    readonly_fields = ["status", "language", "sid", "o_feed", "total_tokens", "total_characters", "size", "modified"]
    actions = ['t_feed_force_update', 't_feed_export_as_opml']

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        queryset |= self.model.objects.filter(o_feed__feed_url__icontains=search_term)
        return queryset, use_distinct
        
    
    def size_in_kb(self, obj):
        return int(obj.size / 1024)

    size_in_kb.short_description = 'Size(KB)'

    def feed_url(self, obj):
        if obj.sid:
            return format_html(
                "<a href='/rss/{0}' target='_blank'>{0}  </a>",
               obj.sid
            )
        return ''

    def has_add_permission(self, request):
        return False
    
    def status_icon(self, obj):
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

    status_icon.short_description = 'Status'
    status_icon.admin_order_field = 'status'

if not settings.USER_MANAGEMENT:
    admin.site.unregister(User)
    admin.site.unregister(Group)
