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
            logging.info("Start translate feed: [%s]%s", feed.target_language, feed.feed_url)

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
            logging.info("Start summary feed: [%s]%s", feed.target_language, feed.feed_url)

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
                    translation_display=feed.translation_display
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
                    translation_display=feed.translation_display,
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
    translation_display: int
)->dict:
    """Translate entry title with caching and retry logic"""
    total_tokens = 0
    total_characters = 0
    # Check if title has been translated
    if entry.translated_title:
        logging.debug("[Title] Title already translated")
        return {"tokens": 0, "characters": 0}

    logging.debug("[Title] Translating title")
    result = _retry_translation(
        engine.translate,
        max_retries=3,
        text=entry.original_title,
        target_language=target_language,
        text_type="title"
    )
    if result:
        translated_text = result.get("text", entry.original_title)
        total_tokens = result.get("tokens", 0)
        total_characters = result.get("characters", 0)
    
        # 更新entry标题
        entry.translated_title = text_handler.set_translation_display(
            original=entry.original_title,
            translation=translated_text,
            translation_display=translation_display,
            seprator=" || ",
        )
    return {"tokens": total_tokens, "characters": total_characters}


def _translate_content(
    entry: Entry,
    target_language: str,
    engine: TranslatorEngine,
    translation_display: int,
    quality: bool = False,
)->dict:
    """Translate entry content with optimized caching"""

    total_tokens = 0
    total_characters = 0
    # 检查是否已经翻译过
    if entry.translated_content:
        logging.debug("[Content] Content already translated")
        return {"tokens": 0, "characters": 0}
    
    # TODO:清理逻辑要优化
    logging.debug("[Content] Translating content")
    soup = BeautifulSoup(entry.original_content, "lxml")
    if quality:
        soup = BeautifulSoup(text_handler.unwrap_tags(soup), "lxml")

    for element in soup.find_all(string=True):
        if text_handler.should_skip(element):
            continue
        # TODO 如果文字长度大于最大长度，就分段翻译，需要用chunk_translate
        text = element.get_text()

    logging.debug("[Content] Translating content")
    result = _retry_translation(
        func=engine.translate,
        max_retries=3,
        text=text,
        target_language=target_language,
        text_type="content"
    )
    translated_text = result.get("text", text)
    total_tokens = result.get("tokens", 0)
    total_characters = result.get("characters", 0)

    # Format translated content
    entry.translated_content = text_handler.set_translation_display(
        original=text,
        translation=translated_text,
        translation_display=translation_display,
        seprator="<br>---------------<br>",
    )

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

    try:
        for entry in feed.entries.all():
            # Check cache first
            if entry.ai_summary:
                logging.debug("[Summary] Summary already generated")
            else:
                logging.debug("[Summary] Generating summary")
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
                        # Creating a structured prompt for recursive summarization
                        accumulated_summaries_string = "\n\n".join(accumulated_summaries)
                        user_message_content = f"Previous summaries:\n\n{accumulated_summaries_string}\n\nText to summarize next:\n\n{chunk}"
                    else:
                        # Directly passing the chunk for summarization without recursive context
                        user_message_content = chunk

                    # Assuming this function gets the completion and works as expected
                    response = _retry_translation(
                        feed.summarizer.summarize,
                        max_retries=3,
                        text=user_message_content,
                        target_language=feed.target_language,
                    )
                    accumulated_summaries.append(response.get("text"))
                    feed.total_tokens += response.get("tokens", 0)

                summary_text = "<br>".join(accumulated_summaries)
            
                # Format summary
                html_summary = f"<br>🤖:{mistune.html(summary_text)}<br>---------------<br>"
                entry.ai_summary = summary_text
                entry.translated_content = html_summary + entry.translated_content
            
                entry.save()
    except Exception as e:
        logging.exception(f"Error summarizing feed {feed.feed_url}: {str(e)}")
        feed.log += f"{timezone.now()} Error summarizing feed {feed.feed_url}: {str(e)}<br>"


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