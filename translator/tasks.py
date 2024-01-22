# from .interface.detector import DetectorFactory
import logging

import cityhash
import feedparser
from huey.contrib.djhuey import task, db_task

from .models import TranslatorEngine, Translated_Content

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
    log.debug("Call task translate_feed: %s", target_language)
    translated_feed = feed
    total_tokens = 0
    translated_characters = 0
    need_cache_objs = {}
    # detector = DetectorFactory().get_detector(detector)

    try:
        for entry in translated_feed.entries:
            # Translate title
            if translate_title:
                cached = engine.is_translated(entry["title"], target_language)
                if not cached:
                    # 因性能问题不使用语言探测，直接翻译，如果不翻译，可以手动取消translate_title
                    # sorce_language = detector.detect(entry["title"])
                    # if sorce_language != target_language:
                    original_content = entry["title"]
                    results = engine.translate(original_content, target_language=target_language)
                    entry["title"] = results["result"]
                    total_tokens += results.get("tokens", 0)
                    translated_characters += len(original_content)

                    log.debug("Save to cache:%s", results["result"])
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
                # else:
                # log.debug("Same language,Skip translate [%s]: %s", target_language, entry["title"])
                else:
                    entry["title"] = cached["result"]
                    # total_tokens += cached.get("tokens") #no need
                    # translated_characters += cached.get("characters")
            # Translate content
            if translate_content:
                pass

    except Exception as e:
        log.error("translate_feed Error: %s", str(e))
    finally:
        if need_cache_objs:
            Translated_Content.objects.bulk_create(need_cache_objs.values())

    return {"feed": translated_feed, "tokens": total_tokens, "characters": translated_characters}
