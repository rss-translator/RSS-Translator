import logging
from ast import literal_eval
from django import forms
from django.contrib import admin
from django.conf import settings
from django.shortcuts import render
from django.urls import path
from django.shortcuts import render,redirect
from django.core.paginator import Paginator
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.utils.html import format_html
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy  as _
from .models import O_Feed, T_Feed
#from taggit.models import Tag
from .tasks import update_original_feed, update_translated_feed
from utils.modelAdmin_utils import CustomModelActions, get_translator_and_summary_choices, get_all_app_models, valid_icon

class CoreAdminSite(admin.AdminSite):
    site_header = _('RSS Translator Admin')
    site_title = _('RSS Translator')
    index_title = _('Dashboard')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("translator/add", translator_add_view, name="translator_add"),
            path("translator/list", translator_list_view, name="translator_list"),
        ]
        return custom_urls + urls
    
    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)
        app_list += [{
                "name": _("Engine"),
                "app_label": "engine",
                "models": [
                    {
                        "name": _("Translator"),
                        "object_name": "Translator",
                        "admin_url": "/translator/list",
                        "add_url": "/translator/add",
                        #"view_only": False,
                    }
                ],
            }
        ]
        
        return app_list
    
core_admin_site = CoreAdminSite()

class TranslatorPaginator(Paginator):
    def __init__(self):
        super().__init__(self, 100)

        self.translator_count = len(get_all_app_models('translator'))

    @property
    def count(self):
        return self.translator_count

    def page(self, number):
        limit = self.per_page
        offset = (number - 1) * self.per_page
        return self._get_page(
            self.enqueued_items(limit, offset),
            number,
            self,
        )

    # Copied from Huey's SqliteStorage with some modifications to allow pagination
    def enqueued_items(self, limit, offset):
        translators = get_all_app_models('translator')
        translator_list = []
        for model in translators:
            objects = model.objects.all().order_by('name').values_list('id', 'name', 'valid')[offset:offset+limit]
            for obj_id, obj_name, obj_valid in objects:
                translator_list.append({'id':obj_id, 'table_name': model._meta.db_table.split('_')[1], 'name':obj_name,'valid': valid_icon(obj_valid), 'provider': model._meta.verbose_name})

        return translator_list
 

def translator_list_view(request):
    page_number = int(request.GET.get("p", 1))
    paginator = TranslatorPaginator()
    page = paginator.get_page(page_number)
    page_range = paginator.get_elided_page_range(page_number, on_each_side=2, on_ends=2)

    context = {
        **core_admin_site.each_context(request),
        "title": "Translator",
        "page": page,
        "page_range": page_range,
        "translators": page.object_list,
    }
    return render(request, 'admin/translator.html', context)

def translator_add_view(request):
    if request.method == 'POST':
        translator_name = request.POST.get('translator_name','/')
        # redirect to example.com/translator/translator_name/add
        target = f"/translator/{translator_name}/add"
        return redirect(target) if url_has_allowed_host_and_scheme(target, allowed_hosts=None) else redirect('/')
    else:
        models = get_all_app_models('translator')
        translator_list = []
        for model in models:
            translator_list.append({'table_name': model._meta.db_table.split('_')[1], 'provider': model._meta.verbose_name})
        context = {
            **core_admin_site.each_context(request),
            "translator_choices": translator_list,
        }
        return render(request, 'admin/translator_add.html', context)

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
    fields = ["language", "obj_status", "feed_url", "translate_title", "translate_content", "summary", "total_tokens",
              "total_characters", "size_in_kb",'sid']
    readonly_fields = ("feed_url", "obj_status", "size_in_kb", "total_tokens", "total_characters")
    extra = 1

    def feed_url(self, obj):
        if obj.sid:
            rss = reverse('core:rss', kwargs={'feed_sid': obj.sid})
            rss_url = self.request.build_absolute_uri(rss)
            json = reverse('core:json', kwargs={'feed_sid': obj.sid})
            json_url = self.request.build_absolute_uri(json)
            return format_html(
                "<a href='{0}' target='_blank'>RSS </a>"
                "<button type='button' class='btn' data-url='{0}' onclick='copyToClipboard(this)'>Copy</button> | "
                "<a href='{1}' target='_blank'>JSON </a>"
                "<button type='button' class='btn' data-url='{1}' onclick='copyToClipboard(this)'>Copy</button>",
                rss_url,json_url
            )
        return ''

    feed_url.short_description = _('Translated Feed URL')

    class Media:
        js = ('js/admin/copytoclipboard.js',)

    def size_in_kb(self, obj):
        return int(obj.size / 1024)

    size_in_kb.short_description = _('Size(KB)')

    def obj_status(self, obj):
        if not obj.pk:
            return ''
        return valid_icon(obj.status)

    obj_status.short_description = _('Status')
    def get_formset(self, request, obj=None, **kwargs):
        # Store the request for use in feed_url
        self.request = request
        return super(T_FeedInline, self).get_formset(request, obj, **kwargs)

class O_FeedForm(forms.ModelForm):
    # 自定义字段，使用ChoiceField生成下拉菜单
    translator = forms.ChoiceField(choices=(), required=False, help_text=_("Select a valid translator"), label=_("Translator"))
    summary_engine = forms.ChoiceField(choices=(), required=False, help_text=_("Select a valid AI engine"), label=_("Summary Engine"))
    def __init__(self, *args, **kwargs):
        super(O_FeedForm, self).__init__(*args, **kwargs)

        self.fields['translator'].choices, self.fields['summary_engine'].choices = get_translator_and_summary_choices()

        # 如果已经有关联的对象，设置默认值
        instance = getattr(self, 'instance', None)
        if instance and instance.pk and instance.content_type and instance.object_id:
            self.fields['translator'].initial = f"{instance.content_type.id}:{instance.object_id}"
            
        if instance and instance.pk and instance.content_type_summary and instance.object_id_summary:
            self.fields['summary_engine'].initial = f"{instance.content_type_summary.id}:{instance.object_id_summary}"
        
        #self.fields['translator'].short_description = _("Translator")

    class Meta:
        model = O_Feed
        fields = ['feed_url', 'update_frequency', 'max_posts', 'translator', 'translation_display', 'summary_engine', 'summary_detail', 'additional_prompt', 'fetch_article', 'quality', 'name', 'category', ]

    # 重写save方法，以处理自定义字段的数据
    def save(self, commit=True):
        # 获取选择的translator，并设置content_type和translator_object_id
        if self.cleaned_data['translator']:
            content_type_id, object_id = map(int, self.cleaned_data['translator'].split(':'))
            self.instance.content_type_id = content_type_id
            self.instance.object_id = object_id
        else:
            self.instance.content_type = None
            self.instance.object_id = None

        if self.cleaned_data['summary_engine']:
            content_type_summary_id, object_id_summary = map(int, self.cleaned_data['summary_engine'].split(':'))
            self.instance.content_type_summary_id = content_type_summary_id
            self.instance.object_id_summary = object_id_summary
        else:
            self.instance.content_type_summary_id = None
            self.instance.object_id_summary = None

        return super(O_FeedForm, self).save(commit=commit)

class O_FeedAdmin(admin.ModelAdmin, CustomModelActions):
    form = O_FeedForm
    inlines = [T_FeedInline]
    list_display = ["name", "is_valid", "show_feed_url", "translated_language", "translator", "size_in_kb",
                    "update_frequency", "last_updated", "last_pull", "category"]
    search_fields = ["name", "feed_url", "category__name"]
    list_filter = ["valid","category"]
    actions = ['o_feed_force_update', 'o_feed_export_as_opml', 'o_feed_batch_modify']


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
        #feed_name_changed = 'name' in form.changed_data
        frequency_changed = 'update_frequency' in form.changed_data
        translation_display_changed = 'translation_display' in form.changed_data
        # translator_changed = 'content_type' in form.changed_data or 'object_id' in form.changed_data
        if feed_url_changed or translation_display_changed:
            obj.valid = None
            obj.name = "Loading" if not obj.name else obj.name
            obj.save()
            update_original_feed.schedule(args=(obj.sid,), delay=1) # 会执行一次save() # 不放在model的save里是为了排除translator的更新，省流量
        elif frequency_changed:
            obj.save()
            self.revoke_tasks_by_arg(obj.sid)
            update_original_feed.schedule(args=(obj.sid,), delay=obj.update_frequency * 60)
        else:
            obj.name = "Empty" if not obj.name else obj.name
            obj.save()
            
    def translator(self, obj):
        return obj.translator
    translator.short_description = _('Translator')

    def translated_language(self, obj):
        return ", ".join(t_feed.language for t_feed in obj.t_feed_set.all())
    translated_language.short_description = _('Translated Language')

    # def get_queryset(self, request):
    #     return super().get_queryset(request).prefetch_related('tags')

    # def tag_list(self, obj):
    #     return ", ".join(o.name for o in obj.tags.all())
    
    def size_in_kb(self, obj):
        return int(obj.size / 1024)

    size_in_kb.short_description = _('Size(KB)')

    def is_valid(self, obj):
        return valid_icon(obj.valid)

    is_valid.short_description = _('Valid')

    is_valid.admin_order_field = 'valid'
    size_in_kb.admin_order_field = 'size'

    @admin.display(description="feed_url")
    def show_feed_url(self, obj):
        if obj.feed_url:
            url = obj.feed_url
            return format_html(
                "<a href='{0}' target='_blank'>{1}...</a>",
                # "<button type='button' class='btn' data-url='{0}' onclick=''>Update</button>",
                url, url[:30]
            )
        return ''
    show_feed_url.short_description = _('Feed URL')

    def proxy_feed_url(self, obj):
        if obj.sid:
            return format_html(
                "<a href='/rss/{0}' target='_blank'>Proxy URL</a>",
                obj.sid
            )
        return ''
    
    def o_feed_batch_modify(self, request, queryset):
        if 'apply' in request.POST:
            logging.info("Apply o_feed_batch_modify")
            post_data = request.POST
            fields = {
                'update_frequency': 'update_frequency_value',
                'max_posts': 'max_posts_value',
                'translator': 'translator_value',
                'translation_display': 'translation_display_value',
                'summary_engine': 'summary_engine_value',
                'summary_detail': 'summary_detail_value', 
                'additional_prompt': 'additional_prompt_value',
                'fetch_article': 'fetch_article',
                'quality': 'quality',
                'category': 'category_value'
            }
            field_types = {
                'update_frequency': int,
                'max_posts': int,
                'translation_display': int,
                'summary_detail': float, 
                'additional_prompt': str,
                'fetch_article': literal_eval,
                'quality': literal_eval        
            }
            update_fields = {}
            #tags_value = None
            
            for field, value_field in fields.items():
                value = post_data.get(value_field)
                if post_data.get(field, 'Keep') != 'Keep' and value:
                    match field:
                        case 'translator':
                            content_type_id, object_id = map(int, value.split(':'))
                            update_fields['content_type_id'] = content_type_id
                            update_fields['object_id'] = object_id
                        case 'summary_engine':
                            content_type_summary_id, object_id_summary = map(int, value.split(':'))
                            update_fields['content_type_summary_id'] = content_type_summary_id
                            update_fields['object_id_summary'] = object_id_summary
                        case 'category':
                            tag_model = O_Feed.category.tag_model
                            category_o, _ = tag_model.objects.get_or_create(name=value)
                            update_fields['category'] = category_o
        
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
                #O_Feed.objects.bulk_update(queryset, ['tags'])??

            #self.message_user(request, f"Successfully modified {queryset.count()} items.")
            #return HttpResponseRedirect(request.get_full_path())
            return redirect(request.get_full_path())
        
        translator_choices, summary_engine_choices = get_translator_and_summary_choices() 
        logging.info("translator_choices: %s, summary_engine_choices: %s", translator_choices, summary_engine_choices)
        return render(request, 'admin/o_feed_batch_modify.html', context={**core_admin_site.each_context(request), 'items': queryset,'translator_choices': translator_choices, 'summary_engine_choices': summary_engine_choices})
    o_feed_batch_modify.short_description = _("Batch modification")
        

class T_FeedAdmin(admin.ModelAdmin, CustomModelActions):
    list_display = ["id", "feed_url", "o_feed", "status_icon", "language", "translate_title", "translate_content", "summary", "total_tokens", "total_characters", "size_in_kb", "modified"]
    list_filter = ["status", "translate_title", "translate_content", "o_feed__category"]
    search_fields = ["sid", "o_feed__category__name", "o_feed__feed_url"]
    readonly_fields = ["status", "language", "sid", "o_feed", "total_tokens", "total_characters", "size", "modified"]
    actions = ['t_feed_force_update', 't_feed_export_as_opml', 't_feed_batch_modify']
    # def get_search_results(self, request, queryset, search_term):
    #     queryset, use_distinct = super().get_search_results(request, queryset, search_term)
    #     queryset |= self.model.objects.filter(o_feed__feed_url__icontains=search_term)
    #     return queryset, use_distinct

    # def get_queryset(self, request):
    #     return super().get_queryset(request).prefetch_related('o_feed__category')
    
    def size_in_kb(self, obj):
        return int(obj.size / 1024)

    size_in_kb.short_description = _('Size(KB)')

    def feed_url(self, obj):
        if obj.sid:
            return format_html(
                "<a href='/rss/{0}' target='_blank'>{0}  </a>",
               obj.sid
            )
        return ''
    feed_url.short_description = _('Translated Feed URL')

    def has_add_permission(self, request):
        return False
    
    def status_icon(self, obj):
        return valid_icon(obj.status)
    
    status_icon.short_description = _('Status')
    status_icon.admin_order_field = 'status'
    
    def t_feed_batch_modify(self, request, queryset):
        if 'apply' in request.POST:
            logging.info("Apply t_feed_batch_modify")
            translate_title = request.POST.get('translate_title', 'Keep')
            translate_content = request.POST.get('translate_content', 'Keep')
            summary = request.POST.get('summary', 'Keep')
            match translate_title:
                case 'Keep':
                    pass
                case "True":
                    queryset.update(translate_title=True)
                case "False":
                    queryset.update(translate_title=False)

            match translate_content:
                case 'Keep':
                    pass
                case "True":
                    queryset.update(translate_content=True)
                case "False":
                    queryset.update(translate_content=False)

            match summary:
                case 'Keep':
                    pass
                case "True":
                    queryset.update(summary=True)
                case "False":
                    queryset.update(summary=False)

            #self.message_user(request, f"Successfully modified {queryset.count()} items.")
            #return HttpResponseRedirect(request.get_full_path())
            return redirect(request.get_full_path())
        return render(request, 'admin/t_feed_batch_modify.html', context={**core_admin_site.each_context(request), 'items': queryset})
    
    t_feed_batch_modify.short_description = _("Batch modification")
   

core_admin_site.register(O_Feed, O_FeedAdmin)
core_admin_site.register(T_Feed, T_FeedAdmin)

if settings.USER_MANAGEMENT:
    core_admin_site.register(User)
    core_admin_site.register(Group)
