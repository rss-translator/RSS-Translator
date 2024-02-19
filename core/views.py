import logging
import os

from django.conf import settings
from django.http import HttpResponse, Http404, StreamingHttpResponse
from django.utils.encoding import smart_str
from django.views.decorators.cache import cache_page
from django.views.decorators.http import etag
from .models import T_Feed

def get_modified(request, feed_sid):
    return T_Feed.objects.get(sid=feed_sid).modified

#@cache_page(60 * 15)  # Cache this view for 15 minutes
@etag(get_modified)
def rss(request, feed_sid):
    # Sanitize the feed_sid to prevent path traversal attacks
    feed_sid = smart_str(feed_sid)

    feed_file_path = os.path.join(settings.DATA_FOLDER, 'feeds', f'{feed_sid}.xml')

    # Check if the file exists and if not, raise a 404 error
    if not os.path.exists(feed_file_path):
        logging.error("Requested feed file not found: %s", feed_file_path)
        raise Http404(f"The feed with ID {feed_sid} does not exist.")

    try:
        # Stream the file content
        def file_iterator(file_name, chunk_size=8192):
            with open(file_name, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

        response = StreamingHttpResponse(file_iterator(feed_file_path),
                                         content_type='application/xml')
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(feed_file_path)}"'
        logging.info("Feed file served: %s", feed_file_path)
        return response
    except IOError as e:
        # Log the exception and return an appropriate error response
        logging.exception("Failed to read the feed file: %s / %s", feed_file_path, str(e))
        return HttpResponse(status=500)
