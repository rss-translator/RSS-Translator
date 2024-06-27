import os
import uuid
import re

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from tagulous.models import SingleTagField


class O_Feed(models.Model):
    sid = models.SlugField(
        max_length=255,
        unique=True,
        editable=False,
    )
    name = models.CharField(_("Name"), max_length=255, blank=True, null=True)
    feed_url = models.URLField(
        _("Feed URL"),
        unique=True,
    )
    last_updated = models.DateTimeField(
        _("Last Updated(UTC)"),
        default=None,
        blank=True,
        null=True,
        editable=False,
        help_text=_("Last updated from the original feed"),
    )
    last_pull = models.DateTimeField(
        _("Last Pull(UTC)"),
        default=None,
        blank=True,
        null=True,
        editable=False,
        help_text=_("Last time the feed was pulled"),
    )
    TRANSLATION_DISPLAY_CHOICES = [
        (0, _("Only Translation")),
        (1, _("Translation | Original")),
        (2, _("Original | Translation")),
    ]
    translation_display = models.IntegerField(
        _("Translation Display"), default=0, choices=TRANSLATION_DISPLAY_CHOICES
    )  # 0: Only Translation, 1: Translation || Original, 2: Original || Translation

    etag = models.CharField(
        max_length=255,
        default="",
        editable=False,
    )
    size = models.IntegerField(
        _("Size"),
        default=0,
        editable=False,
    )
    valid = models.BooleanField(
        _("Valid"),
        null=True,
        editable=False,
    )
    update_frequency = models.IntegerField(
        _("Update Frequency"),
        default=os.getenv("default_update_frequency", 30),
        help_text=_("Minutes"),
    )
    max_posts = models.IntegerField(
        _("Max Posts"),
        default=os.getenv("default_max_posts", 20),
        help_text=_("Max number of posts to be translated"),
    )
    quality = models.BooleanField(
        _("Best Quality"),
        default=False,
        help_text=_(
            "Formatting such as hyperlinks, bold, italics, etc. will be lost for optimal translation quality."
        ),
    )
    fetch_article = models.BooleanField(
        _("Fetch Original Article"),
        default=False,
        help_text=_("Fetch original article from the website."),
    )

    content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, related_name="translator"
    )
    object_id = models.PositiveIntegerField(null=True)
    translator = GenericForeignKey("content_type", "object_id")

    content_type_summary = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, related_name="summary_engine"
    )
    object_id_summary = models.PositiveIntegerField(null=True)
    summary_engine = GenericForeignKey("content_type_summary", "object_id_summary")

    summary_detail = models.FloatField(
        _("Summary Detail"),
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        default=0.0,
        blank=True,
        null=True,
        help_text=_(
            "Level of detail of summaries of longer articles. 0: Normal, 1: Most detailed (cost more tokens)"
        ),
    )

    additional_prompt = models.TextField(
        _("Addtional Prompt"),
        default=None,
        blank=True,
        null=True,
        help_text=_("Addtional Prompt for translation and summary"),
    )
    category = SingleTagField(
        force_lowercase=True, blank=True, help_text=_("Enter a category string")
    )

    def __str__(self):
        return self.feed_url

    class Meta:
        verbose_name = _("Original Feed")
        verbose_name_plural = _("Original Feeds")

    def save(self, *args, **kwargs):
        if not self.sid:
            self.sid = uuid.uuid5(
                uuid.NAMESPACE_URL, f"{self.feed_url}:{settings.SECRET_KEY}"
            ).hex
        super(O_Feed, self).save(*args, **kwargs)

    def get_translation_display(self):
        return dict(self.TRANSLATION_DISPLAY_CHOICES)[self.translation_display]


class T_Feed(models.Model):
    sid = models.SlugField(
        _("URL Slug(Optional)"),
        max_length=255,
        unique=True,
        help_text=_(
            "Example: if set to hacker_news, the subscription address will be http://127.0.0.1:8000/rss/hacker_news"
        ),
    )  # sid for feed_url and file name
    language = models.CharField(
        _("Language"), choices=settings.TRANSLATION_LANGUAGES, max_length=50
    )
    o_feed = models.ForeignKey(
        O_Feed, on_delete=models.CASCADE, verbose_name=_("Original Feed")
    )
    status = models.BooleanField(
        _("Translation Status"),
        null=True,
        editable=False,
    )

    translate_title = models.BooleanField(_("Translate Title"), default=False)
    translate_content = models.BooleanField(_("Translate Content"), default=False)
    summary = models.BooleanField(_("Summary"), default=False)

    total_tokens = models.IntegerField(_("Tokens Cost"), default=0)
    total_characters = models.IntegerField(_("Characters Cost"), default=0)

    modified = models.DateTimeField(
        _("Last Modified"),
        blank=True,
        null=True,
        editable=False,
        help_text=_("Last time the feed was translated"),
    )
    size = models.IntegerField(
        _("Size"),
        default=0,
        editable=False,
    )

    # translate_paragraphs = models.IntegerField(_("Translate Paragraphs"), default=0)

    class Meta:
        verbose_name = _("Translated Feed")
        verbose_name_plural = _("Translated Feeds")
        constraints = [
            models.UniqueConstraint(
                fields=["o_feed", "language"], name="unique_o_feed_lang"
            )
        ]

    def __str__(self):
        return self.sid

    def save(self, *args, **kwargs):
        if not self.sid:
            self.sid = (
                f"{self.o_feed.sid}_{re.sub('[^a-z]', '_', self.language.lower())}"
            )
        # else:
        #     self.sid = self.sid
        super(T_Feed, self).save(*args, **kwargs)
