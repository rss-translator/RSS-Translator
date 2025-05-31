import logging
import os

from django.conf import settings
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Feed
# from taggit.models import TaggedItem


@receiver(post_delete, sender=Feed)
def delete_feed_xml(sender, instance, **kwargs):
    logging.info("Call delete_xml: %s", instance.slug)
    original_feed_file_path = f"{settings.DATA_FOLDER}/feeds/o_{instance.slug}.xml"
    if os.path.exists(original_feed_file_path):
        os.remove(original_feed_file_path)
    translated_feed_file_path = f"{settings.DATA_FOLDER}/feeds/t_{instance.slug}.xml"
    if os.path.exists(translated_feed_file_path):
        os.remove(translated_feed_file_path)
    json_feed_file_path = f"{settings.DATA_FOLDER}/feeds/t_{instance.slug}.json"
    if os.path.exists(json_feed_file_path):
        os.remove(json_feed_file_path)


# @receiver(post_delete, sender=T_Feed)
# def delete_t_feed_xml(sender, instance, **kwargs):
#     logging.info("Call delete_xml: %s", instance.sid)
#     feed_file_path = f"{settings.DATA_FOLDER}/feeds/{instance.sid}.xml"
#     if os.path.exists(feed_file_path):
#         os.remove(feed_file_path)


# For django-taggit
# @receiver(post_delete, sender=TaggedItem)
# def delete_unused_tags(sender, instance, **kwargs):
#     n_tagged = TaggedItem.objects.filter(tag_id=instance.tag_id).count()
#     if n_tagged == 0:
#         instance.tag.delete()
