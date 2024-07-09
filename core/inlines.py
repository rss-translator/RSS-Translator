
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import T_Feed
from .forms import T_FeedForm
from utils.modelAdmin_utils import (
    valid_icon,
)

class T_FeedInline(admin.TabularInline):
    model = T_Feed
    form = T_FeedForm
    fields = [
        "language",
        "obj_status",
        "feed_url",
        "translate_title",
        "translate_content",
        "summary",
        "total_tokens",
        "total_characters",
        "size_in_kb",
        "sid",
    ]
    readonly_fields = (
        "feed_url",
        "obj_status",
        "size_in_kb",
        "total_tokens",
        "total_characters",
    )
    extra = 1

    @admin.display(description=_("Translated Feed URL"))
    def feed_url(self, obj):
        if obj.sid:
            rss = reverse("core:rss", kwargs={"feed_sid": obj.sid})
            rss_url = self.request.build_absolute_uri(rss)
            json = reverse("core:json", kwargs={"feed_sid": obj.sid})
            json_url = self.request.build_absolute_uri(json)
            return format_html(
                "<a href='{0}' target='_blank'>RSS </a>"
                "<button type='button' class='btn' data-url='{0}' onclick='copyToClipboard(this)'>Copy</button> | "
                "<a href='{1}' target='_blank'>JSON </a>"
                "<button type='button' class='btn' data-url='{1}' onclick='copyToClipboard(this)'>Copy</button>",
                rss_url,
                json_url,
            )
        return ""

    class Media:
        js = ("js/admin/copytoclipboard.js",)

    @admin.display(description=_("Size(KB)"))
    def size_in_kb(self, obj):
        return int(obj.size / 1024)

    @admin.display(description=_("Status"))
    def obj_status(self, obj):
        if not obj.pk:
            return ""
        return valid_icon(obj.status)

    def get_formset(self, request, obj=None, **kwargs):
        # Store the request for use in feed_url
        self.request = request
        return super(T_FeedInline, self).get_formset(request, obj, **kwargs)
