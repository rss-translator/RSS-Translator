import logging
import os
import gc
import json
#import xml.dom.minidom
from datetime import datetime, timezone, date, timedelta
from time import mktime
from dateutil import parser
from django.conf import settings

from typing import Dict

import feedparser
import httpx
from lxml import etree
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
        'User-Agent': ua.random.strip()
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
            content = entry.get('content')[0].get('value') if entry.get('content') else None
            summary = entry.get('summary')

            fe = fg.add_entry(order='append')
            fe.title(title)
            fe.link(href=link)
            fe.author({'name': author_name})
            fe.id(unique_id)
            fe.content(content, type='html')
            fe.updated(updated)
            fe.pubDate(pubdate)
            fe.summary(summary, type='html')

            for enclosure in entry.get('enclosures', []):
                fe.enclosure(url=enclosure.get('href'),
                             type=enclosure.get('type'),
                             length=enclosure.get('length'),
                             )

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

    # dom = xml.dom.minidom.parseString(atom_string)
    # pi = dom.createProcessingInstruction("xml-stylesheet", 'type="text/xsl" href="/static/rss.xsl"')
    # dom.insertBefore(pi, dom.firstChild)
    # atom_string_with_pi = dom.toprettyxml()

    root = etree.fromstring(atom_string)
    tree = etree.ElementTree(root)
    pi = etree.ProcessingInstruction("xml-stylesheet", 'type="text/xsl" href="/static/rss.xsl"')
    root.addprevious(pi)
    atom_string_with_pi = etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding='utf-8').decode()

    return atom_string_with_pi


# def atom2jsonfeed(atom_file_path: str) -> dict:
#     feed = feedparser.parse(atom_file_path)

#     json_feed = {
#         "version": "https://jsonfeed.org/version/1.1",
#         "title": feed.feed.title,
#         "feed_url": feed.feed.id,
#         "home_page_url": feed.feed.get("link", None)
#     }

#     if hasattr(feed.feed, "subtitle"):
#         json_feed["description"] = feed.feed.subtitle
#     if hasattr(feed.feed, "updated"):
#         json_feed["updated"] = feed.feed.updated

#     json_feed["items"] = []
#     for entry in feed.entries:
#         item = {
#             "id": entry.id,
#             "url": entry.link,
#             "title": entry.title,
#         }
#         if hasattr(entry, "summary"):
#             item["content_html"] = entry.summary
#         if hasattr(entry, "published"):
#             item["date_published"] = entry.published
#         if hasattr(entry, "updated"):
#             item["date_modified"] = entry.updated
#         if hasattr(entry, "author"):
#             authors = entry.author
#             if not isinstance(authors, list):
#                 authors = [authors]
#             item["authors"] = [{"name": author} for author in authors]
#         if hasattr(entry, "content"):
#             item["content_html"] = ""
#             for content in entry.content:
#                 if content["type"] == "text/html":
#                     item["content_html"] += content["value"]
#                 elif content["type"] == "text/plain":
#                     item["content_text"] = content["value"]

#         json_feed["items"].append(item)

#     return json_feed


def merge_all_atom(input_files:list, filename:str):
    ATOM_NS = "http://www.w3.org/2005/Atom"

    output_dir = os.path.join(settings.DATA_FOLDER, 'feeds')
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f'{filename}.xml')
    with open(os.path.normpath(output_file), 'wb') as f:
        f.write(b'<?xml version="1.0" encoding="utf-8"?>\n')
        f.write(b'<?xml-stylesheet type="text/xsl" href="/static/rss.xsl"?>\n')
        f.write(f'<feed xmlns="{ATOM_NS}">\n'.encode('utf-8'))
        f.write(f'<title>Translated Feeds for {filename} | RSS Translator</title>\n'.encode('utf-8'))
        f.write(b'<link href="https://rsstranslator.com"/>\n')
        f.write(f'<updated>{datetime.now(timezone.utc).isoformat()}</updated>\n'.encode('utf-8'))

        today = date.today()
        thirty_days_ago = today - timedelta(days=30)
        processed_entries = set()

        for input_file in input_files:
            for _, entry in etree.iterparse(input_file, events=('end',), tag=f"{{{ATOM_NS}}}entry"):
                id_elem = entry.find(f"{{{ATOM_NS}}}id")
                if id_elem is not None and id_elem.text not in processed_entries:
                    published_elem = entry.find(f"{{{ATOM_NS}}}published") or entry.find(f"{{{ATOM_NS}}}updated")
                    if published_elem is not None:
                        published_date = parser.parse(published_elem.text).date()
                        if published_date >= thirty_days_ago:
                            f.write(etree.tostring(entry, pretty_print=True))
                            processed_entries.add(id_elem.text)
                entry.clear()
                while entry.getprevious() is not None:
                    del entry.getparent()[0]
            gc.collect()
        f.write(b'</feed>')


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
