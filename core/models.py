import uuid
import re

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _


class O_Feed(models.Model):
    sid = models.CharField(max_length=255, unique=True)
    name = models.CharField(_("Name"), max_length=255, blank=True, null=True)
    feed_url = models.URLField(_("Feed URL"), unique=True,)
    modified = models.CharField(_("Last Modified"), max_length=255, default="",)
    etag = models.CharField(max_length=255, default="")
    size = models.IntegerField(_("Size"), default=0)
    valid = models.BooleanField(_("Valid"), null=True,)
    update_frequency = models.IntegerField(_("Update Frequency(minutes)"), default=30,)

    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True)
    object_id = models.PositiveIntegerField(null=True)
    translator = GenericForeignKey( 'content_type', 'object_id')

    def __str__(self):
        return self.feed_url

    class Meta:
        verbose_name = _("Original Feed")
        verbose_name_plural = _("Original Feeds")


    def save(self, *args, **kwargs):
        if not self.sid:
            self.sid = uuid.uuid5(uuid.NAMESPACE_URL, f"{self.feed_url}:{settings.SECRET_KEY}").hex
        super(O_Feed, self).save(*args, **kwargs)


class T_Feed(models.Model):
    sid = models.CharField(max_length=255, unique=True)  # sid for feed_url and file name
    language = models.CharField(_("Language"), choices=settings.TRANSLATION_LANGUAGES, max_length=50)
    o_feed = models.ForeignKey(O_Feed, on_delete=models.CASCADE, verbose_name=_("Original Feed"))
    status = models.BooleanField(_("Translation Status"), null=True)

    translate_title = models.BooleanField(_("Translate Title"), default=True)
    translate_content = models.BooleanField(_("Translate Content"), default=False)

    total_tokens = models.IntegerField(_("Tokens Cost"), default=0)
    total_characters = models.IntegerField(_("Characters Cost"), default=0)

    modified = models.CharField(_("Last Modified"), max_length=255, default="")
    size = models.IntegerField(_("Size"), default=0)

    class Meta:
        verbose_name = _("Translated Feed")
        constraints = [
            models.UniqueConstraint(fields=['o_feed', 'language'], name='unique_o_feed_lang')
        ]

    def __str__(self):
        return self.sid

    def save(self, *args, **kwargs):
        if not self.sid:
            self.sid = f"{self.o_feed.sid}_{re.sub('[^a-z]', '_', self.language.lower())}"
        super(T_Feed, self).save(*args, **kwargs)
