import logging
import time
from datetime import datetime
from time import mktime
from django.utils.timezone import make_aware
from bs4 import BeautifulSoup
import mistune
import newspaper
from typing import Optional
from django.utils import timezone
from .models import Feed, Entry
from utils.feed_action import fetch_feed
from utils.text_handler import text_handler

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
                datetime.fromtimestamp(mktime(update_time), tz=timezone.utc)
                if update_time
                else datetime.now()
            )
            feed.etag = latest_feed.get("etag", "")
            # Update entries
            if getattr(latest_feed, 'entries', None):
                for entry_data in latest_feed.entries[:feed.max_posts]:
                    # 转换发布时间
                    published = entry_data.get('published_parsed') or entry_data.get('updated_parsed')
                    published_dt = make_aware(datetime.fromtimestamp(mktime(published)), timezone.utc) if published else timezone.now()
                    
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
        except Exception as e:
            logging.exception("Task update_original_feeds %s: %s", feed.feed_url, str(e))
            feed.fetch_status = False
            feed.log += str(e)

    Feed.objects.bulk_update(feeds,fields=[...])

def handle_feeds_translation(feeds: list, target_field: str = "title"):
    for feed in feeds:
        try:
            if not feed.entries.exists():
                continue
            
            feed.translation_status = None
            logging.info("Start translate feed: [%s]%s", feed.language, feed.feed_url)

            translate_feed(feed, target_field=target_field)
            feed.translation_status = True
        except Exception as e:
            logging.error(
                "task translate_feeds (%s)%s: %s",
                feed.language,
                feed.feed_url,
                str(e),
            )
            feed.translation_status = False
            feed.log += str(e)
        
    Feed.objects.bulk_update(feeds,fields=[...])

def handle_feeds_summary(feeds: list):
    for feed in feeds:
        try:
            if not feed.entries.exists():
                continue
            
            feed.translation_status = None
            logging.info("Start summary feed: [%s]%s", feed.language, feed.feed_url)

            summarize_feed(feed)
            feed.translation_status = True
        except Exception as e:
            logging.error(
                "task handle_feeds_summary (%s)%s: %s",
                feed.language,
                feed.feed_url,
                str(e),
            )
            feed.translation_status = False
            feed.log += str(e)
        
    Feed.objects.bulk_update(feeds,fields=[...])

def translate_feed(feed: Feed, target_field: str = "title"):
    """Translate and summarize feed entries with enhanced error handling and caching"""
    logging.info(
        "Translating feed: %s (%s items)", feed.target_language, len(feed.entries)
    )
    total_tokens = 0
    translated_characters = 0

    for entry in feed.entries:
        try:
            logging.debug(f"Processing entry {entry}")
            if not feed.translate_engine:
                raise Exception("Translate Engine Not Set")
                
            # Process title translation
            if target_field == "title" and feed.translate_title:
                entry, metrics = _translate_title(
                    entry=entry,
                    target_language=feed.target_language,
                    engine=feed.translate_engine,
                    translation_display=feed.translation_display
                )
                feed.total_tokens += metrics['tokens']
                feed.total_characters += metrics['characters']
            
            # Process content translation
            if target_field == "content" and feed.translate_content and entry.original_content:
                if feed.fetch_article:
                    entry.original_content = _fetch_article_content(entry.link)
                
                entry, metrics = _translate_content(
                    entry=entry,
                    target_language=feed.target_language,
                    engine=feed.translate_engine,
                    translation_display=feed.translation_display,
                    quality=feed.quality,
                )
                feed.total_tokens += metrics['tokens']
                feed.total_characters += metrics['characters']
        
        except Exception as e:
            logging.error(f"Error processing entry {entry.link}: {str(e)}")
            continue
    
    logging.info(f"Translation completed. Tokens: {total_tokens}, Chars: {translated_characters}")

def _translate_title(
    entry: Entry,
    target_language: str,
    engine: TranslatorEngine,
    translation_display: int
):
    """Translate entry title with caching and retry logic"""
    
    # Check if title has been translated
    if entry.translated_title:
        logging.debug("[Title] Title already translated")
    else:
        logging.debug("[Title] Translating title")
        result = _retry_translation(
            engine.translate,
            max_retries=3,
            text=entry.original_title,
            target_language=target_language,
            text_type="title"
        )
        translated_text = result.get("text", entry.original_title)
        entry.total_tokens += result.get("tokens", 0)
        entry.total_characters += result.get("characters", 0)
    
        # Update entry title with display formatting
        entry.translated_title = text_handler.set_translation_display(
            original=entry.original_title,
            translation=translated_text,
            translation_display=translation_display,
            seprator=" || ",
        )


def _translate_content(
    entry: Entry,
    target_language: str,
    engine: TranslatorEngine,
    translation_display: int,
    quality: bool = False,
):
    """Translate entry content with optimized caching"""

    # TODO:清理逻辑要优化
    soup = BeautifulSoup(entry.original_content, "lxml")
    if quality:
        soup = BeautifulSoup(text_handler.unwrap_tags(soup), "lxml")

    for element in soup.find_all(string=True):
        if text_handler.should_skip(element):
            continue
        # TODO 如果文字长度大于最大长度，就分段翻译，需要用chunk_translate
        text = element.get_text()

    # Check cache first
    if entry.translated_content:
        logging.debug("[Content] Content already translated")
        translated_text = entry.translated_content
    else:
        logging.debug("[Content] Translating content")
        result = _retry_translation(
            func=engine.translate,
            max_retries=3,
            text=text,
            target_language=target_language,
            text_type="content"
        )
        translated_text = result.get("text", text)
        entry.total_tokens += result.get("tokens", 0)
        entry.total_characters += result.get("characters", 0)
    
        # Format translated content
        entry.translated_content = text_handler.set_translation_display(
            original=text,
            translation=translated_text,
            translation_display=translation_display,
            seprator="<br />---------------<br />",
        )

def summarize_feed(
    feed: Feed,
    minimum_chunk_size: Optional[int] = 500,
    chunk_delimiter: str = ".",
    summarize_recursively=True,
):
    """Generate content summary with retry logic"""
    # check detail is set correctly
    assert 0 <= feed.detail <= 1

    for entry in feed.entries:
        # Check cache first
        if entry.ai_summary:
            logging.debug("[Summary] Summary already generated")
        else:
            logging.debug("[Summary] Generating summary")
            max_chunks = len(
                    text_handler.chunk_on_delimiter(
                        text, minimum_chunk_size, chunk_delimiter
                    )
            )
            min_chunks = 1
            num_chunks = int(min_chunks + feed.detail * (max_chunks - min_chunks))

            # adjust chunk_size based on interpolated number of chunks
            document_length = len(text_handler.tokenize(text))
            chunk_size = max(minimum_chunk_size, document_length // num_chunks)
            text_chunks = text_handler.chunk_on_delimiter(
                text, chunk_size, chunk_delimiter
            )
            accumulated_summaries = []
            for chunk in text_chunks:
                if summarize_recursively and accumulated_summaries:
                    # Creating a structured prompt for recursive summarization
                    accumulated_summaries_string = "\n\n".join(accumulated_summaries)
                    user_message_content = f"Previous summaries:\n\n{accumulated_summaries_string}\n\nText to summarize next:\n\n{chunk}"
                else:
                    # Directly passing the chunk for summarization without recursive context
                    user_message_content = chunk

                # Assuming this function gets the completion and works as expected
                response = feed.summarizer.summarize(user_message_content, target_language)
                response = _retry_translation(
                    feed.summarizer.summarize,
                    max_retries=3,
                    text=user_message_content,
                    target_language=target_language,
                )
                accumulated_summaries.append(response.get("text"))
                entry.total_tokens += response.get("tokens", 0)

            summary_text = "<br/>".join(accumulated_summaries)
        
            # Format summary
            html_summary = f"<br />🤖:{mistune.html(summary_text)}<br />---------------<br />"
            entry.ai_summary = summary_text
            entry.translated_content = html_summary + entry.translated_content


def _retry_translation(
    func: callable, 
    max_retries: int = 3, 
    **kwargs
) -> dict:
    """Retry translation function with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return func(**kwargs)
        except Exception as e:
            logging.warning(f"Translation attempt {attempt+1} failed: {str(e)}")
        time.sleep(0.5 * (2 ** attempt))  # Exponential backoff
    logging.error(f"All {max_retries} attempts failed for translation")
    return {}


def _fetch_article_content(link: str) -> str:
    """Fetch full article content using newspaper"""
    try:
        article = newspaper.article(link)
        return mistune.html(article.text)
    except Exception as e:
        logging.warning(f"Article fetch failed: {str(e)}")
    return ""