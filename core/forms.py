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
    simple_update_frequency = forms.ChoiceField(
        choices=([
            (5, "5 min"),
            (15, "15 min"),
            (30, "30 min"),
            (60, _("hourly")),
            (1440, _("daily")),
            (10080, _("weekly")),
        ]),
        required=False,
        help_text=_("Select a valid update frequency"),
        label=_("Update Frequency"),
        initial=60,
    )
    translate_options = forms.MultipleChoiceField(
            choices=(
                ("title", _("Title")),
                ("content", _("Content")),
                ("summary", _("Summary")),
            ),
            required=False,
            label=_("Translation Options"),
            widget=forms.CheckboxSelectMultiple,
            initial=[],
        )

    class Meta:
        model = Feed
        exclude = ["fetch_status", "translation_status", 'translator', 'summary_engine']
        fields = [
            "feed_url",
            "name",
            "slug",
            "max_posts",
            "simple_update_frequency", # 自定义字段
            "translate_options",
            "target_language",
            "translator_option",  # 自定义字段
            "summary_engine_option",  # 自定义字段
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
        
        #如果是已创建的对象，设置默认值
        instance = getattr(self, "instance", None)
        if instance and instance.pk:
            self._set_initial_values(instance)


    def _set_initial_values(self, instance):
        if instance.translator_content_type and instance.translator_object_id:
            self.fields["translator_option"].initial = f"{instance.translator_content_type.id}:{instance.translator_object_id}"
        if instance.summary_content_type and instance.summary_object_id:
            self.fields["summary_engine_option"].initial = f"{instance.summary_content_type.id}:{instance.summary_object_id}"
        if instance.update_frequency:
            self.fields["simple_update_frequency"].initial = instance.update_frequency
        if instance.translate_title:
            self.fields["translate_options"].initial.append("title")
        if instance.translate_content:
            self.fields["translate_options"].initial.append("content")
        if instance.summary:
            self.fields["translate_options"].initial.append("summary")

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
    
    def _process_update_frequency(self, instance):
        if self.cleaned_data["simple_update_frequency"]:
            instance.update_frequency = int(self.cleaned_data["simple_update_frequency"])
        else:
            instance.update_frequency = 60

    def _process_translate_options(self, instance):
        if self.cleaned_data["translate_options"]:
            translate_options = self.cleaned_data["translate_options"]
            if "title" in translate_options:
                instance.translate_title = True
            else:
                instance.translate_title = False
            if "content" in translate_options:
                instance.translate_content = True
            else:
                instance.translate_content = False
            if "summary" in translate_options:
                instance.summary = True
            else:
                instance.summary = False

    # 重写save方法，以处理自定义字段的数据
    @transaction.atomic
    def save(self, commit=True):
        instance = super(FeedForm, self).save(commit=False)

        self._process_translator(instance)
        self._process_summary_engine(instance)
        self._process_update_frequency(instance)
        self._process_translate_options(instance)

        if commit:
            instance.save()
        
        return instance