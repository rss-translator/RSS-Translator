import os
import uuid
# import re

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from tagulous.models import SingleTagField

class Feed(models.Model):
    name = models.CharField( max_length=255, blank=True, null=True, verbose_name=_("Name"))
    slug = models.SlugField(
        _("URL Slug"),
        max_length=255,
        unique=True,
        blank=True,
        null=True,
        help_text=_(
            "Example: if set to hacker_news, the subscription address will be http://127.0.0.1:8000/rss/hacker_news"
        ),
    )
    feed_url = models.URLField(
        _("Feed URL")
    )
    fetch_status = models.BooleanField(
        _("Fetch Status"),
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

    TRANSLATION_DISPLAY_CHOICES = [
        (0, _("Only Translation")),
        (1, _("Translation | Original")),
        (2, _("Original | Translation")),
    ]
    translation_display = models.IntegerField(
        _("Translation Display"), default=0, choices=TRANSLATION_DISPLAY_CHOICES
    )  # 0: Only Translation, 1: Translation || Original, 2: Original || Translation

    target_language = models.CharField(
        _("Language"), choices=settings.TRANSLATION_LANGUAGES, max_length=50, default=settings.DEFAULT_TARGET_LANGUAGE
    )
    translate_title = models.BooleanField(_("Translate Title"), default=False)
    translate_content = models.BooleanField(_("Translate Content"), default=False)
    summary = models.BooleanField(_("Summary"), default=False)

    translation_status = models.BooleanField(
        _("Translation Status"),
        null=True,
        editable=False,
    )

    translator_content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, related_name="translator"
    )
    translator_object_id = models.PositiveIntegerField(null=True)
    translator = GenericForeignKey("translator_content_type", "translator_object_id")


    summary_content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, related_name="summarizer"
    )
    summary_object_id = models.PositiveIntegerField(null=True)
    summarizer = GenericForeignKey("summary_content_type", "summary_object_id")

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

    total_tokens = models.IntegerField(_("Tokens Cost"), default=0)
    total_characters = models.IntegerField(_("Characters Cost"), default=0)

    last_translate = models.DateTimeField(
        _("Last translate"),
        blank=True,
        null=True,
        editable=False,
        help_text=_("Last time the feed was translated"),
    )
    
    last_fetch = models.DateTimeField(
        _("Last Fetch(UTC)"),
        default=None,
        blank=True,
        null=True,
        editable=False,
        help_text=_("Last time the feed was fetched"),
    )
    etag = models.CharField(
        max_length=255,
        default="",
        editable=False,
    )
    
    log = models.TextField(
        _("Log"),
        default="",
        blank=True,
        null=True,
        help_text=_("Log for the feed, useful for debugging"),
    )


    def __str__(self):
        return self.feed_url

    class Meta:
        verbose_name = _("Feed")
        verbose_name_plural = _("Feeds")
        constraints = [
            models.UniqueConstraint(
                fields=["feed_url", "target_language"], name="unique_feed_lang"
            )
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = uuid.uuid5(
                uuid.NAMESPACE_URL, f"{self.feed_url}:{self.target_language}:{settings.SECRET_KEY}"
            ).hex

        thresholds = [5, 15, 30, 60, 1440, 10080]
        for threshold in thresholds:
            if self.update_frequency <= threshold:
                self.update_frequency = threshold
                break
        
        if len(self.log.encode('utf-8')) > 2048:
            self.log = self.log[-2048:]

        super(Feed, self).save(*args, **kwargs)

    def get_translation_display(self):
        return dict(self.TRANSLATION_DISPLAY_CHOICES)[self.translation_display]

class Entry(models.Model):
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, related_name="entries")
    link = models.URLField(null=False)
    created = models.DateTimeField(db_index=True)
    guid = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    
    original_title = models.CharField(max_length=255, null=True, blank=True)
    translated_title = models.CharField(max_length=255, null=True, blank=True)
    original_content = models.TextField(null=True, blank=True)
    translated_content = models.TextField(null=True, blank=True)
    original_summary = models.TextField(null=True, blank=True)
    ai_summary = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return self.original_title  

    class Meta:
        verbose_name = _("Entry")
        verbose_name_plural = _("Entries")
        constraints = [
            models.UniqueConstraint(
                fields=["feed", "guid"], name="unique_entry_guid"
            )
        ]
    