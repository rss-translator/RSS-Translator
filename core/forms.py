from django import forms
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from .models import O_Feed, T_Feed
from utils.modelAdmin_utils import get_translator_and_summary_choices

class O_FeedForm(forms.ModelForm):
    # 自定义字段，使用ChoiceField生成下拉菜单
    translator = forms.ChoiceField(
        choices=(),
        required=False,
        help_text=_("Select a valid translator"),
        label=_("Translator"),
    )
    summary_engine = forms.ChoiceField(
        choices=(),
        required=False,
        help_text=_("Select a valid AI engine"),
        label=_("Summary Engine"),
    )

    def __init__(self, *args, **kwargs):
        super(O_FeedForm, self).__init__(*args, **kwargs)
        self.fields["translator"].choices, self.fields["summary_engine"].choices = (
            get_translator_and_summary_choices()
        )

        # 如果已经有关联的对象，设置默认值
        instance = getattr(self, "instance", None)
        if instance and instance.pk:
            self._set_initial_values(instance)

    def _set_initial_values(self, instance):
        if instance.content_type and instance.object_id:
            self.fields["translator"].initial = f"{instance.content_type.id}:{instance.object_id}"
        if instance.content_type_summary and instance.object_id_summary:
            self.fields["summary_engine"].initial = f"{instance.content_type_summary.id}:{instance.object_id_summary}"

    class Meta:
        model = O_Feed
        fields = [
            "feed_url",
            "update_frequency",
            "max_posts",
            "translator",
            "translation_display",
            "summary_engine",
            "summary_detail",
            "additional_prompt",
            "fetch_article",
            "quality",
            "name",
            "category",
        ]

    def _process_translator(self, instance):
        if self.cleaned_data["translator"]:
            content_type_id, object_id = map(int, self.cleaned_data["translator"].split(":"))
            instance.content_type_id = content_type_id
            instance.object_id = object_id
        else:
            instance.content_type = None
            instance.object_id = None

    def _process_summary_engine(self, instance):
        if self.cleaned_data["summary_engine"]:
            content_type_summary_id, object_id_summary = map(int, self.cleaned_data["summary_engine"].split(":"))
            instance.content_type_summary_id = content_type_summary_id
            instance.object_id_summary = object_id_summary
        else:
            instance.content_type_summary_id = None
            instance.object_id_summary = None

    # 重写save方法，以处理自定义字段的数据
    @transaction.atomic
    def save(self, commit=True):
        instance = super(O_FeedForm, self).save(commit=False)

        self._process_translator(instance)
        self._process_summary_engine(instance)

        if commit:
            instance.save()
        
        return instance

class T_FeedForm(forms.ModelForm):
    class Meta:
        model = T_Feed
        fields = ["language", "translate_title", "sid"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sid"].required = False
        if self.instance.pk:
            self.fields["language"].disabled = True
            self.fields["sid"].disabled = True