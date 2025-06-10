import logging
import time
from django.utils import timezone
from bs4 import BeautifulSoup
import mistune
import newspaper
from typing import Optional
from .models import Feed, Entry
from utils.feed_action import fetch_feed
from utils import text_handler
from translator.models import TranslatorEngine


def handle_feeds_fetch(feeds: list):
    """
    Fetch feeds and update entries.
    """
    for feed in feeds:
        try:
            feed.fetch_status = None
            fetch_results = fetch_feed(url=feed.feed_url, etag=feed.etag)


            if fetch_results["error"]:
                raise Exception(f"Fetch Feed Failed: {fetch_results['error']}")
            elif not fetch_results["update"]:
                raise Exception("Feed is up to date, Skip")
            
            latest_feed = fetch_results.get("feed")
            # Update feed meta
            if not feed.name or feed.name in ["Loading", "Empty"]:
                feed.name = latest_feed.feed.get("title") or latest_feed.feed.get("subtitle", "Empty")

            update_time = latest_feed.feed.get("updated_parsed")
            feed.last_fetch = (
                timezone.datetime.fromtimestamp(time.mktime(update_time), tz=timezone.get_default_timezone())
                if update_time
                else timezone.now()
            )
            feed.etag = latest_feed.get("etag", "")
            # Update entries
            if getattr(latest_feed, 'entries', None):
                for entry_data in latest_feed.entries[:feed.max_posts]:
                    # 转换发布时间
                    published = entry_data.get('published_parsed') or entry_data.get('updated_parsed')
                    published_dt = timezone.datetime.fromtimestamp(
                        time.mktime(published),
                        tz=timezone.get_default_timezone()
                    ) if published else timezone.now()
                    
                    # 获取内容
                    content = ""
                    if 'content' in entry_data:
                        content = entry_data.content[0].value if entry_data.content else ""
                    else:
                        content = entry_data.get('summary', '')
                    
                    guid = entry_data.get('id') or entry_data.get('link')
                    if not guid:
                        continue  # 跳过无效条目

                    # 创建或更新条目
                    Entry.objects.update_or_create(
                        feed=feed,
                        guid=guid,
                        defaults={
                            'link': entry_data.get('link', ''),
                            'created': published_dt,
                            'original_title': entry_data.get('title', 'No title'),
                            'original_content': content,
                            'original_summary': entry_data.get('summary', '')
                        }
                    )
            feed.fetch_status = True
            feed.log = f"{timezone.now()} Fetch Completed <br>"
        except Exception as e:
            logging.exception("Task handle_feeds_fetch %s: %s", feed.feed_url, str(e))
            feed.fetch_status = False
            feed.log = f"{timezone.now()} {str(e)}<br>"

    Feed.objects.bulk_update(feeds,fields=["fetch_status", "last_fetch", "etag", "log", "name"])

def handle_feeds_translation(feeds: list, target_field: str = "title"):
    for feed in feeds:
        try:
            if not feed.entries.exists():
                continue
            
            feed.translation_status = None
            logging.info("Start translate %s of feed %s to %s", target_field,feed.feed_url, feed.target_language)

            translate_feed(feed, target_field=target_field)
            feed.translation_status = True
            feed.log += f"{timezone.now()} Translate Completed <br>"
        except Exception as e:
            logging.exception(
                "Task handle_feeds_translation (%s)%s: %s",
                feed.target_language,
                feed.feed_url,
                str(e),
            )
            feed.translation_status = False
            feed.log += f"{timezone.now()} {str(e)} <br>"
        
    Feed.objects.bulk_update(feeds,fields=["translation_status", "log", "total_tokens", "total_characters"])

def handle_feeds_summary(feeds: list):
    for feed in feeds:
        try:
            if not feed.entries.exists():
                continue
            
            feed.translation_status = None
            logging.info("Start summary feed %s to %s", feed.feed_url, feed.target_language)

            summarize_feed(feed)
            feed.translation_status = True
            feed.log += f"{timezone.now()} Summary Completed <br>"
        except Exception as e:
            logging.exception(
                "Task handle_feeds_summary (%s)%s: %s",
                feed.target_language,
                feed.feed_url,
                str(e),
            )
            feed.translation_status = False
            feed.log += f"{timezone.now()} {str(e)}<br>"
        
    Feed.objects.bulk_update(feeds,fields=["translation_status", "log", "total_tokens", "total_characters"])

def translate_feed(feed: Feed, target_field: str = "title"):
    """Translate and summarize feed entries with enhanced error handling and caching"""
    logging.info(
        "Translating feed: %s (%s items)", feed.target_language, feed.entries.count()
    )
    total_tokens = 0
    total_characters = 0
    entries_to_save = []

    for entry in feed.entries.all():
        try:
            logging.debug(f"Processing entry {entry}")
            if not feed.translator:
                raise Exception("Translate Engine Not Set")
            
            entry_needs_save = False

            # Process title translation
            if target_field == "title" and feed.translate_title:
                metrics = _translate_title(
                    entry=entry,
                    target_language=feed.target_language,
                    engine=feed.translator,
                )
                total_tokens += metrics['tokens']
                total_characters += metrics['characters']
                entry_needs_save = True
            
            # Process content translation
            if target_field == "content" and feed.translate_content and entry.original_content:
                if feed.fetch_article:
                    article_content = _fetch_article_content(entry.link)
                    if article_content:
                        entry.original_content = article_content
                        entry_needs_save = True
                
                metrics = _translate_content(
                    entry=entry,
                    target_language=feed.target_language,
                    engine=feed.translator,
                    quality=feed.quality,
                )
                total_tokens += metrics['tokens']
                total_characters += metrics['characters']
                entry_needs_save = True

            if entry_needs_save:
                entries_to_save.append(entry)

        except Exception as e:
            logging.exception(f"Error processing entry {entry.link}: {str(e)}")
            feed.log += f"{timezone.now()} Error processing entry {entry.link}: {str(e)}<br>"
            continue

    # 批量保存所有修改过的entry
    if entries_to_save:
        Entry.objects.bulk_update(
            entries_to_save,
            fields=[
                "translated_title", 
                "translated_content", 
                "original_content"
            ]
        )
    
    # 更新feed的统计信息（将在外层批量更新中保存）
    feed.total_tokens += total_tokens
    feed.total_characters += total_characters

    logging.info(f"Translation completed. Tokens: {total_tokens}, Chars: {total_characters}")

def _translate_title(
    entry: Entry,
    target_language: str,
    engine: TranslatorEngine,
)->dict:
    """Translate entry title with caching and retry logic"""
    total_tokens = 0
    total_characters = 0
    # Check if title has been translated
    if entry.translated_title:
        logging.debug(f"[Title] Title already translated: {entry.original_title}")
        return {"tokens": 0, "characters": 0}

    logging.debug("[Title] Translating title")
    result = _auto_retry(
        engine.translate,
        max_retries=3,
        text=entry.original_title,
        target_language=target_language,
        text_type="title"
    )
    if result:
        entry.translated_title = result.get("text", entry.original_title)
        total_tokens = result.get("tokens", 0)
        total_characters = result.get("characters", 0)
    return {"tokens": total_tokens, "characters": total_characters}


def _translate_content(
    entry: Entry,
    target_language: str,
    engine: TranslatorEngine,
    quality: bool = False,
)->dict: # TODO: Force update会执行2次
    """Translate entry content with optimized caching"""
    total_tokens = 0
    total_characters = 0
    # 检查是否已经翻译过
    if entry.translated_content:
        logging.debug(f"[Content] Content already translated: {entry.original_title}")
        return {"tokens": 0, "characters": 0}
    
    soup = BeautifulSoup(entry.original_content, "lxml")
    # if quality:
    #     soup = BeautifulSoup(text_handler.unwrap_tags(soup), "lxml")

    # add notranslate class and translate="no" to elements that should not be translated
    for element in soup.find_all(string=True):
        if not element.get_text(strip=True):
            continue
        if text_handler.should_skip(element):
            logging.debug("[Content] Skipping element %s", element.parent)
            # 标记父元素不翻译
            parent = element.parent
            parent.attrs.update({
                'class': parent.get('class', []) + ['notranslate'],
                'translate': 'no'
            })

    # TODO 如果文字长度大于最大长度，就分段翻译
    processed_html = str(soup)

    logging.debug(f"[Content] Translating content: {entry.original_title}")
    result = _auto_retry(
        func=engine.translate,
        max_retries=3,
        text=processed_html,
        target_language=target_language,
        text_type="content"
    )
    entry.translated_content = result.get("text", processed_html)
    total_tokens = result.get("tokens", 0)
    total_characters = result.get("characters", 0)

    return {"tokens": total_tokens, "characters": total_characters}

def summarize_feed(
    feed: Feed,
    minimum_chunk_size: Optional[int] = 500,
    chunk_delimiter: str = ".",
    summarize_recursively=True,
):
    """Generate content summary with retry logic"""
    # check detail is set correctly
    assert 0 <= feed.summary_detail <= 1
    entries_to_save = []
    try:
        for entry in feed.entries.all():
            entry_needs_save = False
            # Check cache first
            if entry.ai_summary:
                logging.debug(f"[Summary] Summary already generated: {entry.original_title}")
            else:
                logging.debug(f"[Summary] Generating summary: {entry.original_title}")
                max_chunks = len(
                        text_handler.chunk_on_delimiter(
                            entry.original_content, minimum_chunk_size, chunk_delimiter
                        )
                )
                min_chunks = 1
                num_chunks = int(min_chunks + feed.summary_detail * (max_chunks - min_chunks))

                # adjust chunk_size based on interpolated number of chunks
                document_length = len(text_handler.tokenize(entry.original_content))
                chunk_size = max(minimum_chunk_size, document_length // num_chunks)
                text_chunks = text_handler.chunk_on_delimiter(
                    entry.original_content, chunk_size, chunk_delimiter
                )
                accumulated_summaries = []
                for chunk in text_chunks:
                    if summarize_recursively and accumulated_summaries:
                        accumulated_summaries_string = "\n\n".join(accumulated_summaries)
                        user_message_content = f"Previous summaries:\n\n{accumulated_summaries_string}\n\nText to summarize next:\n\n{chunk}"
                    else:
                        user_message_content = chunk

                    response = _auto_retry(
                        feed.summarizer.summarize,
                        max_retries=3,
                        text=user_message_content,
                        target_language=feed.target_language,
                    )
                    accumulated_summaries.append(response.get("text"))
                    feed.total_tokens += response.get("tokens", 0)

                entry.ai_summary = "<br>".join(accumulated_summaries)
                entry_needs_save = True

            if entry_needs_save:
                entries_to_save.append(entry)
    except Exception as e:
        logging.exception(f"Error summarizing feed {feed.feed_url}: {str(e)}")
        feed.log += f"{timezone.now()} Error summarizing feed {feed.feed_url}: {str(e)}<br>"
    finally:
        if entries_to_save:
            Entry.objects.bulk_update(
                entries_to_save,
                fields=[
                    "ai_summary"
                ]
            )


def _auto_retry(
    func: callable, 
    max_retries: int = 3, 
    **kwargs
) -> dict:
    """Retry translation function with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return func(**kwargs)
        except Exception as e:
            logging.exception(f"Translation attempt {attempt+1} failed: {str(e)}")
        time.sleep(0.5 * (2 ** attempt))  # Exponential backoff
    logging.error(f"All {max_retries} attempts failed for translation")
    return {}


def _fetch_article_content(link: str) -> str:
    """Fetch full article content using newspaper"""
    try:
        article = newspaper.article(link)
        return mistune.html(article.text)
    except Exception as e:
        logging.exception(f"Article fetch failed: {str(e)}")
    return ""