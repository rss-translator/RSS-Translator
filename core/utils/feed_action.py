import logging
import xml.dom.minidom
from datetime import datetime
from typing import Dict

import feedparser
import httpx
from django.utils.feedgenerator import Atom1Feed


def fetch_feed(url: str, modified: str = "", etag: str = "") -> Dict:
    update = False
    feed = {}
    error = None

    headers = {
        'If-None-Match': etag,
        'If-Modified-Since': modified
    }

    def log_request(request):
        logging.debug("Request: %s %s - Waiting for response", request.method, request.url)

    def log_response(response):
        request = response.request
        logging.debug("Response: %s %s - Status %s", request.method, request.url, response.status_code)

    client = httpx.Client(event_hooks={'request': [log_request], 'response': [log_response]})

    try:
        response = client.get(url, headers=headers, timeout=30, follow_redirects=True)
        response.raise_for_status()

        if response.status_code == 200:
            feed = feedparser.parse(response.text)
            update = True
        elif response.status_code == 304:
            update = False

    except httpx.HTTPStatusError as exc:
        error = f"HTTP status error while requesting {url}: {exc.response.status_code}"
    except httpx.TimeoutException:
        error = f"Timeout while requesting {url}"
    except Exception as e:
        error = f"Error while requesting {url}: {str(e)}"

    if feed:
        feed["entries"] = feed["entries"][:1000]
        if feed.bozo and not feed.entries:
            logging.warning("Get feed %s %s", url, feed.get("bozo_exception"))

    return {"feed": feed, "xml": response.text if response else "", "update": update, "error": error}


def generate_atom_feed(feed_dict: dict):
    """
    Generate an Atom feed from a dictionary parsed by feedparser.
    """
    source_feed = feed_dict['feed']
    # https://feedparser.readthedocs.io/en/latest/reference.html
    pubdate = source_feed.get('published_parsed')
    pubdate = datetime(*pubdate[:6]) if pubdate else None

    updated = source_feed.get('updated_parsed')
    updated = datetime(*updated[:6]) if updated else None
    feed = Atom1Feed(
        title=get_first_non_none(source_feed, 'title', 'title_detail'),
        link=get_first_non_none(source_feed, 'link', 'links'),
        description=get_first_non_none(source_feed, 'subtitle', 'subtitle_detail', 'info', 'info_detail',
                                       'title_detail', 'description'),
        language=source_feed.get('language'),
        author_name=get_first_non_none(source_feed, 'author', 'author_detail'),
        updated=updated or pubdate,
    )

    for entry in feed_dict.get('entries'):
        pubdate = entry.get('published_parsed')
        pubdate = datetime(*pubdate[:6]) if pubdate else None

        updated = entry.get('updated_parsed')
        updated = datetime(*updated[:6]) if updated else None

        feed.add_item(
            # https://github.com/django/django/blob/c7e986fc9f4848bd757d4b9b70a40586d2cee9fb/django/utils/feedgenerator.py#L343
            title=get_first_non_none(entry, 'title', 'title_detail'),
            link=get_first_non_none(entry, 'link', 'links'),
            pubdate=pubdate,
            updateddate=updated,
            unique_id=entry.get('id'),
            author_name=get_first_non_none(entry, 'author', 'author_detail'),
            description=get_first_non_none(entry, 'summary', 'summary_detail', 'content', 'title_detail'),
        )

    atom_string = feed.writeString('utf-8')
    dom = xml.dom.minidom.parseString(atom_string)
    pi = dom.createProcessingInstruction("xml-stylesheet", 'type="text/xsl" href="/static/rss.xsl"')
    dom.insertBefore(pi, dom.firstChild)
    atom_string_with_pi = dom.toprettyxml()
    return atom_string_with_pi


def get_first_non_none(feed, *keys):
    return next((feed.get(key) for key in keys if feed.get(key) is not None), None)
