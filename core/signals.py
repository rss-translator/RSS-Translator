import logging
import os

from django.conf import settings
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import O_Feed, T_Feed

@receiver(post_delete, sender=O_Feed)
def delete_o_feed_xml(sender, instance, **kwargs):
    logging.info("Call delete_xml: %s", instance.sid)
    feed_file_path = f"{settings.DATA_FOLDER}/feeds/{instance.sid}.xml"
    if os.path.exists(feed_file_path):
        os.remove(feed_file_path)

@receiver(post_delete, sender=T_Feed)
def delete_t_feed_xml(sender, instance, **kwargs):
    logging.info("Call delete_xml: %s", instance.sid)
    feed_file_path = f"{settings.DATA_FOLDER}/feeds/{instance.sid}.xml"
    if os.path.exists(feed_file_path):
        os.remove(feed_file_path)
