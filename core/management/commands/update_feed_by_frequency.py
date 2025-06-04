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
        need_update_feeds = Feed.objects.filter(update_frequency=update_frequency[simple_update_frequency])
        handle_feeds_fetch(need_update_feeds)

        # 筛选需要translate_title为True的feed
        handle_feeds_translation(need_update_feeds.filter(translate_title=True), target_field="title")

        # 筛选需要translate_content为True的feed
        handle_feeds_translation(need_update_feeds.filter(translate_content=True), target_field="content")

        # 筛选需要summary为True的feed
        handle_feeds_summary(need_update_feeds.filter(summary=True))

        # TODO:export feeds as rss
        # TODO:export feeds as json
    except Exception as e:
        logging.exception("Command update_feeds %s: %s", simple_update_frequency, str(e))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_frequency = sys.argv[1]
    else:
        print("Error: Please specify a valid update frequency ('5 min', '15 min', '30 min', 'hourly', 'daily', 'weekly')")
        sys.exit(1)
    
    update_feeds_by_frequency(simple_update_frequency=target_frequency)