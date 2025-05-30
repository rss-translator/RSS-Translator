from django import forms
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from .models import Feed
from utils.modelAdmin_utils import get_translator_and_summary_choices

class FeedForm(forms.ModelForm):
    # 自定义字段，使用ChoiceField生成下拉菜单
    translator_option = forms.ChoiceField(
        choices=(),
        required=False,
        help_text=_("Select a valid translator"),
        label=_("Translator"),
    )
    summary_engine_option = forms.ChoiceField(
        choices=(),
        required=False,
        help_text=_("Select a valid AI engine"),
        label=_("Summary Engine"),
    )

    class Meta:
        model = Feed
        exclude = ["fetch_status", "translation_status", 'translator', 'summary_engine']
        fields = [
            "feed_url",
            "name",
            "slug",
            "target_language",
            "translator_option",  # 自定义字段
            "summary_engine_option",  # 自定义字段
            "update_frequency",
            "max_posts",
            "translation_display",
            "fetch_article",
            "quality",
            "category",
            "summary_detail",
            "additional_prompt",
        ]

    def __init__(self, *args, **kwargs):
        super(FeedForm, self).__init__(*args, **kwargs)
        
        # 获取翻译器和摘要引擎的选择项
        self.fields["translator_option"].choices, self.fields["summary_engine_option"].choices = (
            get_translator_and_summary_choices()
        )
        
        self.fields["name"].widget.attrs.update({
            'placeholder': _('Optonal, default use the feed title'),
        })

        self.fields["slug"].widget.attrs.update({
            'placeholder': _('Optional, default use the random slug'),
        })
        # self.fields["log"].widget = forms.Textarea(attrs={
        #         'readonly': True,
        #         'rows': 5,  # 设置行数
        #         'cols': 80,  # 设置列数
        #         'style': 'resize: none; overflow-y: auto;',
        #         'class': 'form-control',
        #     })
        #如果是已创建的对象，设置默认值
        instance = getattr(self, "instance", None)
        if instance and instance.pk:
            self._set_initial_values(instance)
            # self.fields["log"].widget = forms.Textarea(attrs={
            #     'readonly': True,
            #     'rows': 5,  # 设置行数
            #     'cols': 80,  # 设置列数
            #     'style': 'resize: none; overflow-y: auto;',
            #     'class': 'form-control',
            # })
        # else:
        #     # 如果是新对象，则不显示相关字段
        #     del self.fields["log"]
        #     del self.fields["total_tokens"]
        #     del self.fields["total_characters"]
        #     del self.fields["size"]
        #     del self.fields["last_fetch"]
        #     del self.fields["translation_status"]
        #     del self.fields["fetch_status"]

    def _set_initial_values(self, instance):
        if instance.translator_content_type and instance.translator_object_id:
            self.fields["translator_option"].initial = f"{instance.translator_content_type.id}:{instance.translator_object_id}"
        if instance.summary_content_type and instance.summary_object_id:
            self.fields["summary_engine_option"].initial = f"{instance.summary_content_type.id}:{instance.summary_object_id}"

    def _process_translator(self, instance):
        if self.cleaned_data["translator_option"]:
            content_type_id, object_id = map(int, self.cleaned_data["translator_option"].split(":"))
            instance.translator_content_type_id = content_type_id
            instance.translator_object_id = object_id
        else:
            instance.translator_content_type_id = None
            instance.translator_object_id = None

    def _process_summary_engine(self, instance):
        if self.cleaned_data["summary_engine_option"]:
            summary_content_type_id, summary_object_id = map(int, self.cleaned_data["summary_engine_option"].split(":"))
            instance.summary_content_type_id = summary_content_type_id
            instance.summary_object_id = summary_object_id
        else:
            instance.summary_content_type_id = None
            instance.summary_object_id = None

    # 重写save方法，以处理自定义字段的数据
    @transaction.atomic
    def save(self, commit=True):
        instance = super(FeedForm, self).save(commit=False)

        self._process_translator(instance)
        self._process_summary_engine(instance)

        if commit:
            instance.save()
        
        return instance