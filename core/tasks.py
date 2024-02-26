from datetime import datetime, timezone
import logging
import os
from pathlib import Path
from time import mktime

import feedparser
from django.conf import settings
from django.utils import timezone
from huey.contrib.djhuey import HUEY as huey
from huey.contrib.djhuey import on_startup, on_shutdown, task
from translator.tasks import translate_feed

from .models import O_Feed, T_Feed
from utils.feed_action import fetch_feed, generate_atom_feed

# from huey_monitor.models import TaskModel

# @periodic_task(crontab( minute='*/1'))
@on_startup()
def schedule_update():
    feeds = O_Feed.objects.all()
    tasks = huey.scheduled() + huey.pending()
    task_feeds = {task.args[0] for task in tasks if task.args}

    for feed in feeds:
        if feed.sid not in task_feeds:
            update_original_feed.schedule(args=(feed.sid,), delay=feed.update_frequency * 60)

#@on_shutdown()
# def flush_all():
#     huey.storage.flush_queue()
#     huey.storage.flush_schedule()
#     huey.storage.flush_results()
    # clean TaskModel all data
    # TaskModel.objects.all().delete()


@task(retries=3)
def update_original_feed(sid: str):
    try:
        obj = O_Feed.objects.get(sid=sid)
    except O_Feed.DoesNotExist:
        return False

    logging.info("Call task update_original_feed: %s", obj.feed_url)
    feed_dir_path = Path(settings.DATA_FOLDER) / "feeds"

    if not os.path.exists(feed_dir_path):
        os.makedirs(feed_dir_path)

    original_feed_file_path = feed_dir_path / f"{obj.sid}.xml"
    try:
        obj.valid = False
        fetch_feed_results = fetch_feed(url=obj.feed_url, etag=obj.etag)

        if fetch_feed_results['error']:
            raise Exception(f"Fetch Original Feed Failed: {fetch_feed_results['error']}")
        elif not fetch_feed_results.get("update"):
            logging.info("Original Feed is up to date, Skip:%s",obj.feed_url)
        else:
            with open(original_feed_file_path, "w", encoding="utf-8") as f:
                f.write(fetch_feed_results.get("xml"))
            feed = fetch_feed_results.get("feed")
            if obj.name in ["Loading", "Empty", None]:
                obj.name = feed.feed.get('title') or feed.feed.get('subtitle')
            obj.size = os.path.getsize(original_feed_file_path)
            update_time = feed.feed.get("updated_parsed")
            obj.last_updated = datetime.fromtimestamp(mktime(update_time), tz=timezone.utc) if update_time else ''
            obj.last_pull = timezone.now()
            obj.etag = feed.get("etag", '')

        obj.valid = True
        update_original_feed.schedule(args=(obj.sid,), delay=obj.update_frequency * 60)
    except Exception as e:
        logging.error("task update_original_feed %s: %s", obj.feed_url, str(e))
    finally:
        obj.save()

    # Update T_Feeds
    t_feeds = obj.t_feed_set.all()
    for t_feed in t_feeds:
        t_feed.status = None
        t_feed.save()
        update_translated_feed.schedule(args=(t_feed.sid,), delay=1)


@task(retries=3)
def update_translated_feed(sid: str, force=False):
    try:
        obj = T_Feed.objects.get(sid=sid)
    except T_Feed.DoesNotExist:
        logging.error(f"T_Feed Not Found: {sid}")
        return False

    try:
        logging.info("Call task update_translated_feed")

        if obj.o_feed.pk is None:
            raise Exception("Unable translate feed, because Original Feed is None")

        if not force and obj.modified == obj.o_feed.last_pull:
            logging.info("Translated Feed is up to date, Skip translation: %s",obj.o_feed.feed_url)
            obj.status = True
            obj.save()
            return True

        feed_dir_path = f"{settings.DATA_FOLDER}/feeds"
        if not os.path.exists(feed_dir_path):
            os.makedirs(feed_dir_path)

        original_feed_file_path = f"{feed_dir_path}/{obj.o_feed.sid}.xml"
        if not os.path.exists(original_feed_file_path):
            update_original_feed(obj.o_feed.sid)
            return False

        translated_feed_file_path = f"{feed_dir_path}/{obj.sid}.xml"
        if not os.path.exists(translated_feed_file_path):
            with open(translated_feed_file_path, "w", encoding="utf-8") as f:
                f.write("Translation in progress...")

        original_feed = feedparser.parse(original_feed_file_path)

        if original_feed.entries:
            engine = obj.o_feed.translator
            logging.info("Start translate feed: [%s]%s" , obj.language, obj.o_feed.feed_url)
            results = translate_feed.call_local(
                feed=original_feed,
                target_language=obj.language,
                engine=engine,
                translate_title=obj.translate_title,
                translate_content=obj.translate_content,
                max_posts=obj.o_feed.max_posts
            )

            if not results:
                raise Exception("Translate Feed Failed")
            else:
                feed = results.get("feed")
                total_tokens = results.get("tokens")
                translated_characters = results.get("characters")
            xml_str = generate_atom_feed(obj.o_feed.feed_url, feed)  # feed is a feedparser object

            if xml_str is None:
                raise Exception("generate_atom_feed returned None")
            with open(translated_feed_file_path, "w", encoding="utf-8") as f:
                f.write(xml_str)

            # There can only be one billing method at a time, either token or character count.
            if total_tokens > 0:
                obj.total_tokens += total_tokens
            else:
                obj.total_characters += translated_characters

            obj.modified = obj.o_feed.last_pull
            obj.size = os.path.getsize(translated_feed_file_path)
            obj.status = True
    except Exception as e:
        logging.error("task update_translated_feed (%s)%s: %s", obj.language, obj.o_feed.feed_url, str(e))
        obj.status = False
    finally:
        obj.save()
