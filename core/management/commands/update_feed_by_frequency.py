import logging
import sys
from django.db.models import Q
from .models import Feed
from core.tasks import handle_feeds_fetch, handle_feeds_translation, handle_feeds_summary

def update_feeds_by_frequency(simple_update_frequency: str):
    """
    Update feeds with given update frequency.
    """
    update_frequency = {
    "5 min": 5,
    "15 min": 15,
    "30 min": 30,
    "hourly": 60,
    "daily": 1440,
    "weekly": 10080,
    }
    
    try:
        need_fetch_feeds = Feed.objects.filter(update_frequency=update_frequency[simple_update_frequency])
        fetched_feeds = handle_feeds_fetch(need_fetch_feeds)
        Feed.objects.bulk_update(fetched_feeds,fields=[...])

        # 筛选需要translate_title或translate_content为True的feed
        need_translate_feeds = fetched_feeds.filter(Q(translate_title=True) | Q(translate_content=True))
        handle_feeds_translation(need_translate_feeds)
        Feed.objects.bulk_update(need_translate_feeds,fields=[...])

        # 筛选需要summary为True的feed
        need_summary_feeds = fetched_feeds.filter(summary=True)
        handle_feeds_summary(need_summary_feeds)
        Feed.objects.bulk_update(need_summary_feeds,fields=[...])

        # TODO:export feeds as rss
        # TODO:export feeds as json
    except Exception as e:
        logging.exception("Command update_feeds %s: %s", simple_update_frequency, str(e))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 使用第一个命令行参数作为频率值
        frequency = sys.argv[1]
    else:
        frequency = "hourly"
    
    # 调用函数并传入频率参数
    update_feeds_by_frequency(simple_update_frequency=frequency)