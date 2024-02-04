# from .interface.detector import DetectorFactory
import logging

import cityhash
import feedparser
from huey.contrib.djhuey import task, db_task

from .models import TranslatorEngine, Translated_Content
from utils import chunk_handler
from utils.feed_action import get_first_non_none

log = logging.getLogger('huey')


@task(retries=3)
def translator_validate(obj: TranslatorEngine):  # TODO ?
    try:
        obj.valid: bool = obj.validate()
    except Exception as e:
        obj.valid = False
    finally:
        obj.save()


@db_task()
def translate_feed(
        feed: feedparser.FeedParserDict,
        target_language: str,
        translate_title: bool,
        translate_content: bool,
        engine: TranslatorEngine) -> dict:
    log.info("Call task translate_feed: %s(%s items)", target_language, len(feed.entries))
    translated_feed = feed
    total_tokens = 0
    translated_characters = 0
    need_cache_objs = {}

    try:
        for entry in translated_feed.entries:
            # Translate title
            if translate_title:
                title = entry["title"]
                cached = engine.is_translated(entry["title"], target_language)
                if not cached:
                    original_content = title
                    results = engine.translate(original_content, target_language=target_language)
                    entry["title"] = results["result"] if results["result"] else original_content
                    total_tokens += results.get("tokens", 0)
                    translated_characters += len(original_content)

                    if original_content and results["result"]:
                        log.info("Save to cache:%s", results["result"])
                        hash64 = cityhash.CityHash64(
                            f"{original_content}{target_language}")  # 在同一次翻译中，可能存在重复的情况，但几率很小，所以重复翻译不影响
                        need_cache_objs[hash64] = Translated_Content(
                            hash=hash64.to_bytes(8, byteorder='little'),
                            original_content=original_content,
                            translated_language=target_language,
                            translated_content=results["result"],
                            tokens=results.get("tokens", 0),
                            characters=results.get("characters", 0),
                        )
                else:
                    entry["title"] = cached["result"]

            # Translate content
            if translate_content:
                original_description = entry.get('summary', None)  # summary, description
                original_content = entry['content'][0].value if entry.get('content') else None  # description, content

                if original_description:
                    translated_summary, tokens, characters, need_cache = chunk_translate(original_description,
                                                                                         target_language, engine)
                    total_tokens += tokens
                    translated_characters += characters
                    need_cache_objs.update(need_cache)
                    entry["summary"] = "".join(translated_summary)

                if original_content:
                    translated_content, tokens, characters, need_cache = chunk_translate(original_content,
                                                                                         target_language, engine)
                    total_tokens += tokens
                    translated_characters += characters
                    need_cache_objs.update(need_cache)
                    entry['content'][0].value = "".join(translated_content)


    except Exception as e:
        log.error("translate_feed Error: %s", str(e))
    finally:
        try:
            if need_cache_objs:
                Translated_Content.objects.bulk_create(need_cache_objs.values())
        except Exception as e:
            log.error("Save cache Error: %s", str(e))

    return {"feed": translated_feed, "tokens": total_tokens, "characters": translated_characters}


def chunk_translate(original_content: str, target_language: str, engine: TranslatorEngine):
    logging.info("Call chunk_translate: %s(%s items)", target_language, len(original_content))
    split_chunks: dict = chunk_handler.content_split(original_content)
    grouped_chunks: list = chunk_handler.group_chunks(split_chunks=split_chunks, min_size=engine.min_size(),
                                                      max_size=engine.max_size(),
                                                      group_by="characters")
    translated_content = []
    total_tokens = 0
    total_characters = 0
    need_cache_objs: dict = {}
    for chunk in grouped_chunks:
        logging.info("Translate chunk: %s", chunk)
        cached = engine.is_translated(chunk, target_language)
        if not cached:
            results = engine.translate(chunk, target_language=target_language)
            translated_content.append(results["result"] if results["result"] else chunk)
            total_tokens += results.get("tokens", 0)
            total_characters += len(chunk)

            if chunk and results["result"]:
                log.info("Save to cache:%s", results["result"])
                hash64 = cityhash.CityHash64(
                    f"{chunk}{target_language}")
                need_cache_objs[hash64] = Translated_Content(
                    hash=hash64.to_bytes(8, byteorder='little'),
                    original_content=chunk,
                    translated_language=target_language,
                    translated_content=results["result"],
                    tokens=results.get("tokens", 0),
                    characters=results.get("characters", 0),
                )
        else:
            translated_content.append(cached["result"])
    return "".join(translated_content), total_tokens, total_characters, need_cache_objs
