import logging
import xml.dom.minidom
from datetime import datetime, timezone
from time import mktime

from typing import Dict

import feedparser
import httpx
# from django.utils.feedgenerator import Atom1Feed
from feedgen.feed import FeedGenerator
from fake_useragent import UserAgent


def fetch_feed(url: str, etag: str = "") -> Dict:
    update = False
    feed = {}
    error = None
    response = None
    ua = UserAgent()
    headers = {
        'If-None-Match': etag,
        #'If-Modified-Since': modified,
        'User-Agent': ua.random
    }

    client = httpx.Client()

    try:
        response = client.get(url, headers=headers, timeout=30, follow_redirects=True)

        if response.status_code == 200:
            feed = feedparser.parse(response.text)
            update = True
        elif response.status_code == 304:
            update = False
        else:
            response.raise_for_status()

    except httpx.HTTPStatusError as exc:
        error = f"HTTP status error while requesting {url}: {exc.response.status_code} {exc.response.reason_phrase}"
    except httpx.TimeoutException:
        error = f"Timeout while requesting {url}"
    except Exception as e:
        error = f"Error while requesting {url}: {str(e)}"

    if feed:
        if feed.bozo and not feed.entries:
            logging.warning("Get feed %s %s", url, feed.get("bozo_exception"))
            error = feed.get("bozo_exception")

    return {"feed": feed, "xml": response.text if response else "", "update": update, "error": error}


def generate_atom_feed(feed_url: str, feed_dict: dict):
    if not feed_dict:
        logging.error("generate_atom_feed: feed_dict is None")
        return None
    try:
        source_feed = feed_dict['feed']
        pubdate = source_feed.get('published_parsed')
        pubdate = datetime.fromtimestamp(mktime(pubdate), tz=timezone.utc) if pubdate else None

        updated = source_feed.get('updated_parsed')
        updated = datetime.fromtimestamp(mktime(updated), tz=timezone.utc) if updated else None

        title = get_first_non_none(source_feed, 'title', 'subtitle', 'info')
        subtitle = get_first_non_none(source_feed, 'subtitle')
        link = source_feed.get('link') or feed_url
        language = source_feed.get('language')
        author_name = source_feed.get('author')
        # logging.info("generate_atom_feed:%s,%s,%s,%s,%s",title,subtitle,link,language,author_name)

        fg = FeedGenerator()
        fg.id(source_feed.get('id', link))
        fg.title(title)
        fg.author({'name': author_name})
        fg.link(href=link, rel='alternate')
        fg.subtitle(subtitle)
        fg.language(language)
        fg.updated(updated)
        fg.pubDate(pubdate)

        if not fg.updated():
            fg.updated(pubdate if pubdate else datetime.now(timezone.utc))
        if not fg.title():
            fg.title(updated.strftime("%Y-%m-%d %H:%M:%S"))
        if not fg.id():
            fg.id(fg.title())

        for entry in feed_dict['entries']:
            pubdate = entry.get('published_parsed')
            pubdate = datetime.fromtimestamp(mktime(pubdate), tz=timezone.utc) if pubdate else None

            updated = entry.get('updated_parsed')
            updated = datetime.fromtimestamp(mktime(updated), tz=timezone.utc) if updated else None

            title = entry.get('title')
            link = get_first_non_none(entry, 'link')
            unique_id = entry.get('id', link)

            author_name = get_first_non_none(entry, 'author', 'publisher')
            content = entry.get('content')[0].value if entry.get('content') else None
            summary = entry.get('summary')

            fe = fg.add_entry()
            fe.title(title)
            fe.link(href=link)
            fe.author({'name': author_name})
            fe.id(unique_id)
            fe.content(content)
            fe.updated(updated)
            fe.pubDate(pubdate)
            fe.summary(summary)

            # id, title, updated are required
            if not fe.updated():
                fe.updated(pubdate if pubdate else datetime.now(timezone.utc))
            if not fe.title():
                fe.title(updated.strftime("%Y-%m-%d %H:%M:%S"))
            if not fe.id():
                fe.id(fe.title())

        # fg.atom_file(file_path, extensions=True, pretty=True, encoding='UTF-8', xml_declaration=True)
        atom_string = fg.atom_str(pretty=False)

    except Exception as e:
        logging.error("generate_atom_feed error %s: %s", feed_url, str(e))
        return None

    dom = xml.dom.minidom.parseString(atom_string)
    pi = dom.createProcessingInstruction("xml-stylesheet", 'type="text/xsl" href="/static/rss.xsl"')
    dom.insertBefore(pi, dom.firstChild)
    atom_string_with_pi = dom.toprettyxml()

    return atom_string_with_pi


def get_first_non_none(feed, *keys):
    return next((feed.get(key) for key in keys if feed.get(key) is not None), None)


''' old generate_atom_feed function, use django feedgenerator
def generate_atom_feed_old(feed_url:str, feed_dict: dict):
    """
    Generate an Atom feed from a dictionary parsed by feedparser.
    """
    if not feed_dict:
        logging.error("generate_atom_feed: feed_dict is None")
        return None
    try:
        source_feed = feed_dict['feed']
        # https://feedparser.readthedocs.io/en/latest/reference.html
        pubdate = source_feed.get('published_parsed')
        pubdate = datetime(*pubdate[:6]) if pubdate else ''

        updated = source_feed.get('updated_parsed')
        updated = datetime(*updated[:6]) if updated else ''
        feed = Atom1Feed(
            title=get_first_non_none(source_feed, 'title', 'subtitle', 'info'),
            link=get_first_non_none(source_feed, 'link', feed_url),
            description=get_first_non_none(source_feed, 'subtitle', 'info', 'description'),
            language=source_feed.get('language'),
            author_name=get_first_non_none(source_feed, 'author'),
            updated=updated or pubdate,
        )

        for entry in feed_dict.get('entries'):
            pubdate = entry.get('published_parsed')
            pubdate = datetime(*pubdate[:6]) if pubdate else ''

            updated = entry.get('updated_parsed')
            updated = datetime(*updated[:6]) if updated else ''

            feed.add_item(
                # https://github.com/django/django/blob/c7e986fc9f4848bd757d4b9b70a40586d2cee9fb/django/utils/feedgenerator.py#L343
                title=entry.get('title',''),
                link=get_first_non_none(entry, 'link'),
                pubdate=pubdate,
                updateddate=updated,
                unique_id=entry.get('id'),
                author_name=get_first_non_none(entry, 'author', 'publisher'),
                description=get_first_non_none(entry, 'content', 'summary'),
            )
    except Exception as e:
        logging.error("generate_atom_feed error: %s", str(e))
    finally:
        atom_string = feed.writeString('utf-8')
        dom = xml.dom.minidom.parseString(atom_string)
        pi = dom.createProcessingInstruction("xml-stylesheet", 'type="text/xsl" href="/static/rss.xsl"')
        dom.insertBefore(pi, dom.firstChild)
        atom_string_with_pi = dom.toprettyxml()
        return atom_string_with_pi

'''
