from django.conf import settings
from pathlib import Path
import os
from datetime import datetime
from feedparser import feedparser
from time import mktime
from django.utils import timezone
from django.db.models import Q
from .models import Feed, Entry
from .utils import fetch_feed
from .translate_feed import translate_feed, summarize_feed


def update_feeds(simple_update_frequency: str):
    update_frequency = {
    "5 min": 5,
    "15 min": 15,
    "30 min": 30,
    "hourly": 60,
    "daily": 1440,
    "weekly": 10080,
    }
    feed_dir_path = Path(settings.DATA_FOLDER) / "feeds"
    if not os.path.exists(feed_dir_path):
        os.makedirs(feed_dir_path)
    
    need_fetch_feeds = Feed.objects.filter(update_frequency=update_frequency[simple_update_frequency])
    fetched_feeds = handle_feeds_fetch(need_fetch_feeds,feed_dir_path)
    Feed.objects.bulk_update(fetched_feeds,fields=[...])

    # 筛选需要translate_title或translate_content为True的feed
    need_translate_feeds = fetched_feeds.filter(Q(translate_title=True) | Q(translate_content=True))
    handle_feeds_translation(need_translate_feeds,feed_dir_path)
    Feed.objects.bulk_update(need_translate_feeds,fields=[...])

    # 筛选需要summary为True的feed
    need_summary_feeds = fetched_feeds.filter(summary=True)
    handle_feeds_summary(need_summary_feeds,feed_dir_path)
    Feed.objects.bulk_update(need_summary_feeds,fields=[...])

    # TODO:export feeds as rss
    # TODO:export feeds as json
    

def handle_feeds_fetch(feeds: list) -> list:
    fetched_feeds = []
    for feed in feeds:
        try:
            feed.fetch_status = None
            fetch_feed_results = fetch_feed(url=feed.feed_url, etag=feed.etag)
            error = fetch_feed_results["error"]
            update = fetch_feed_results.get("update")
            latest_feed: feedparser.FeedParserDict = fetch_feed_results.get("feed")

            if error:
                raise Exception(f"Fetch Feed Failed: {error}")
            elif not update:
                raise Exception("Feed is up to date, Skip")
            else:
                if feed.name in ["Loading", "Empty", None]:
                    feed.name = latest_feed.feed.get("title") or latest_feed.feed.get("subtitle", "Empty")
                update_time = latest_feed.feed.get("updated_parsed")
                feed.last_fetch = (
                    datetime.fromtimestamp(mktime(update_time), tz=timezone.utc)
                    if update_time
                    else datetime.now(timezone.utc)
                )
                feed.etag = feed.get("etag", "")

                if hasattr(latest_feed, 'entries') and latest_feed.entries:
                    for entry_data in latest_feed.entries[:feed.max_posts]:
                        # 转换发布时间
                        published = entry_data.get('published_parsed') or entry_data.get('updated_parsed')
                        published_dt = make_aware(datetime.fromtimestamp(mktime(published))) if published else timezone.now()
                        
                        # 创建或更新条目
                        entry_obj, _ = entry.objects.update_or_create(
                            feed=feed,
                            guid=entry_data.get('id', entry_data.get('link')),
                            defaults={
                                'link': entry_data.get('link', ''),
                                'created': published_dt,
                                'original_title': entry_data.get('title', 'No title'),
                                'original_content': entry_data.get('content', [{}])[0].get('value', '') if 'content' in entry_data else entry_data.get('summary', ''),
                                'original_summary': entry_data.get('summary', '')
                            }
                        )
                        feed.entries.add(entry_obj)

            fetched_feeds.append(feed)

            feed.fetch_status = True
        except Exception as e:
            logging.exception("Task update_original_feeds %s: %s", feed.feed_url, str(e))
            feed.fetch_status = False

    return fetched_feeds

def handle_feeds_translation(fetched_feeds: list):
    for feed in fetched_feeds:
        try:
            if feed.entries:
                feed.translate_status = None
                logging.info("Start translate feed: [%s]%s", feed.language, feed.feed_url)
                results = translate_feed(feed)
                if not results:
                    raise Exception("Translate Feed Failed")
                else:
                    feed = results.get("feed")
                    total_tokens = results.get("tokens")
                    translated_characters = results.get("characters")
                
                # There can only be one billing method at a time, either token or character count.
                if total_tokens > 0:
                    feed.total_tokens += total_tokens
                else:
                    feed.total_characters += translated_characters

                feed.status = True
        except Exception as e:
            logging.error(
                "task translate_feeds (%s)%s: %s",
                feed.language,
                feed.feed_url,
                str(e),
            )
            feed.status = False

def handle_feeds_summary(fetched_feeds: list):
    for feed in fetched_feeds:
        try:
            if feed.entries:
                feed.translate_status = None
                logging.info("Start summary feed: [%s]%s", feed.language, feed.feed_url)
                results = summarize_feed(feed)
                if not results:
                    raise Exception("Summary Feed Failed")
                else:
                    feed = results.get("feed")
                    total_tokens = results.get("tokens")
                    feed.total_tokens += total_tokens

                feed.translate_status = True
        except Exception as e:
            logging.error(
                "task handle_feeds_summary (%s)%s: %s",
                feed.language,
                feed.feed_url,
                str(e),
            )
            feed.translate_status = False

def translate_feed(feed: Feed) -> dict:
    """Translate and summarize feed entries with enhanced error handling and caching"""
    logging.info(
        "Translating feed: %s (%s items)", feed.target_language, len(feed.entries)
    )
    total_tokens = 0
    translated_characters = 0

    try:
        for entry in feed.entries:
            try:
                logging.debug(f"Processing entry {entry}")
                
                # Fetch full article content if requested
                if feed.fetch_article:
                    entry.original_content = _fetch_article_content(entry.link)
                
                # Process title translation
                if feed.translate_title and feed.translate_engine:
                    entry, metrics = _translate_title(
                        entry=entry,
                        target_language=feed.target_language,
                        engine=feed.translate_engine,
                        translation_display=feed.translation_display
                    )
                    total_tokens += metrics['tokens']
                    translated_characters += metrics['characters']
                
                # Process content translation
                if feed.translate_content and entry.original_content and feed.translate_engine:
                    entry, metrics = _translate_content(
                        entry=entry,
                        target_language=feed.target_language,
                        engine=feed.translate_engine,
                        translation_display=feed.translation_display,
                        quality=feed.quality,
                    )
                    total_tokens += metrics['tokens']
                    translated_characters += metrics['characters']
            
            except Exception as e:
                logging.error(f"Error processing entry {entry.link}: {str(e)}")
                continue
    
    except Exception as e:
        logging.exception("Critical error in feed processing")
    
    logging.info(f"Translation completed. Tokens: {total_tokens}, Chars: {translated_characters}")
    return {
        "feed": feed,
        "tokens": total_tokens,
        "characters": translated_characters,
    }

def _translate_title(
    entry: Entry,
    target_language: str,
    engine: TranslatorEngine,
    translation_display: int
) -> tuple:
    """Translate entry title with caching and retry logic"""
    original_title = entry.original_title
    if not original_title:
        return entry, {'tokens': 0, 'characters': 0}
    
    # Check if title has been translated
    if entry.translated_title:
        logging.debug("[Title] Title already translated")
        translated_text = entry.translated_title
        tokens_used = 0
    else:
        logging.debug("[Title] Translating title")
        result = _retry_translation(
            engine.translate,
            max_retries=3,
            text=original_title,
            target_language=target_language,
            text_type="title"
        )
        translated_text = result.get("text", original_title)
        tokens_used = result.get("tokens", 0)
        characters = result.get("characters", len(original_title))
    
        # Update entry title with display formatting
        entry.translated_title = text_handler.set_translation_display(
            original=original_title,
            translation=translated_text,
            translation_display=translation_display,
            seprator=" || ",
        )
    
    return entry, {'tokens': tokens_used, 'characters': characters}


def _translate_content(
    entry: Entry,
    target_language: str,
    engine: TranslatorEngine,
    translation_display: int,
    quality: bool = False,
) -> tuple:
    """Translate entry content with optimized caching"""

    # TODO:清理逻辑要优化
    soup = BeautifulSoup(content, "lxml")
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
        tokens_used = 0
        characters = 0
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
        tokens_used = result.get("tokens", 0)
        characters = result.get("characters", len(text))
    
        # Format translated content
        formatted_text = text_handler.set_translation_display(
            original=text,
            translation=translated_text,
            translation_display=translation_display,
            seprator="<br />---------------<br />",
        )
    
        entry.translated_content = formatted_text
    
    return entry, {'tokens': tokens_used, 'characters': characters}


def summarize_feed(
    feed: Feed,
    minimum_chunk_size: Optional[int] = 500,
    chunk_delimiter: str = ".",
    summarize_recursively=True,
) -> tuple:
    """Generate content summary with retry logic"""
    # check detail is set correctly
    assert 0 <= feed.detail <= 1

    for entry in feed.entries:
        # Check cache first
        if entry.ai_summary:
            logging.debug("[Summary] Summary already generated")
            summary_text = entry.ai_summary
            tokens_used = 0
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
                response = engine.summarize(user_message_content, target_language)
                response = _retry_translation(
                    engine.summarize,
                    max_retries=3,
                    text=user_message_content,
                    target_language=target_language,
                )
                accumulated_summaries.append(response.get("text"))
                tokens_used = response.get("tokens", 0)

            summary_text = "<br/>".join(accumulated_summaries)
        
            # Format summary
            html_summary = f"<br />🤖:{mistune.html(summary_text)}<br />---------------<br />"
            entry.ai_summary = summary_text
            entry.content = html_summary + entry.content
        
    return {"feed": feed, "tokens": tokens_used}


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


if __name__ == "__main__":
    update_feed()