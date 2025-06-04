import logging
import sys
from django.core.management.base import BaseCommand
from core.models import Feed
from core.tasks import handle_feeds_fetch, handle_feeds_translation, handle_feeds_summary

class Command(BaseCommand):
    help = 'Updates feeds based on specified frequency or runs immediate update'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--frequency', 
            type=str,
            nargs='?',  # 可选参数
            help="Specify update frequency ('5 min', '15 min', '30 min', 'hourly', 'daily', 'weekly')"
        )
    
    def handle(self, *args, **options):
        target_frequency = options['frequency']
        
        if target_frequency:
            valid_frequencies = ['5 min', '15 min', '30 min', 'hourly', 'daily', 'weekly']
            if target_frequency not in valid_frequencies:
                self.stderr.write(f"Error: Invalid frequency. Valid options: {', '.join(valid_frequencies)}")
                sys.exit(1)
            try:
                update_feeds_for_frequency(simple_update_frequency=target_frequency)
                self.stdout.write(self.style.SUCCESS(
                    f'Successfully updated feeds for frequency: {target_frequency}'
                ))
            except Exception as e:
                logging.exception(f"Command update_feeds_for_frequency failed: {str(e)}")
                self.stderr.write(self.style.ERROR(f'Error: {str(e)}'))
                sys.exit(1)


def update_feeds_immediately(feeds: list):
    try:
        handle_feeds_fetch(feeds)
        title_trans_feeds = [f for f in feeds if f.translate_title]
        handle_feeds_translation(title_trans_feeds, target_field="title")
        
        content_trans_feeds = [f for f in feeds if f.translate_content]
        handle_feeds_translation(content_trans_feeds, target_field="content")
        
        summary_feeds = [f for f in feeds if f.summary]
        handle_feeds_summary(summary_feeds)
        
    except Exception as e:
        logging.exception("Command update_feeds_immediately failed: %s", str(e))

def update_feeds_for_frequency(simple_update_frequency: str):
    """
    Update feeds for given update frequency group.
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
        logging.info("Start update feeds for frequency: %s", simple_update_frequency)
        update_feeds_immediately(Feed.objects.filter(update_frequency=update_frequency[simple_update_frequency]))

        # TODO:export feeds as rss
        # TODO:export feeds as json
    except Exception as e:
        logging.exception("Command update_feeds_for_frequency %s: %s", simple_update_frequency, str(e))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_frequency = sys.argv[1]
    else:
        print("Error: Please specify a valid update frequency ('5 min', '15 min', '30 min', 'hourly', 'daily', 'weekly')")
        sys.exit(1)
    
    update_feeds_for_frequency(simple_update_frequency=target_frequency)