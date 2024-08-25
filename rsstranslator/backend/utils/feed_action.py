import logging
import os
# import json

# import xml.dom.minidom
from datetime import datetime, timezone, timedelta
from time import mktime

# from dateutil import parser
from django.conf import settings

from typing import Dict

import feedparser
import httpx
from lxml import etree

from feedgen.feed import FeedGenerator
from fake_useragent import UserAgent


def get_first_non_none(feed, *keys):
    return next((feed.get(key) for key in keys if feed.get(key) is not None), None)


def fetch_feed(url: str, etag: str = "") -> Dict:
    update = False
    feed = {}
    error = None
    response = None
    ua = UserAgent()
    headers = {
        "If-None-Match": etag,
        #'If-Modified-Since': modified,
        "User-Agent": ua.random.strip(),
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

    return {
        "feed": feed,
        "xml": response.text if response else "",
        "update": update,
        "error": error,
    }


def generate_atom_feed(feed_url: str, feed_dict: dict):
    if not feed_dict:
        logging.error("generate_atom_feed: feed_dict is None")
        return None
    try:
        source_feed = feed_dict["feed"]
        pubdate = source_feed.get("published_parsed")
        pubdate = (
            datetime.fromtimestamp(mktime(pubdate), tz=timezone.utc)
            if pubdate
            else None
        )

        updated = source_feed.get("updated_parsed")
        updated = (
            datetime.fromtimestamp(mktime(updated), tz=timezone.utc)
            if updated
            else None
        )

        title = get_first_non_none(source_feed, "title", "subtitle", "info")
        subtitle = get_first_non_none(source_feed, "subtitle")
        link = source_feed.get("link") or feed_url
        language = source_feed.get("language")
        author_name = source_feed.get("author")
        # logging.info("generate_atom_feed:%s,%s,%s,%s,%s",title,subtitle,link,language,author_name)

        fg = FeedGenerator()
        fg.id(source_feed.get("id", link))
        fg.title(title)
        fg.author({"name": author_name})
        fg.link(href=link, rel="alternate")
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

        for entry in feed_dict["entries"]:
            pubdate = entry.get("published_parsed")
            pubdate = (
                datetime.fromtimestamp(mktime(pubdate), tz=timezone.utc)
                if pubdate
                else None
            )

            updated = entry.get("updated_parsed")
            updated = (
                datetime.fromtimestamp(mktime(updated), tz=timezone.utc)
                if updated
                else None
            )

            title = entry.get("title")
            link = get_first_non_none(entry, "link")
            unique_id = entry.get("id", link)

            author_name = get_first_non_none(entry, "author", "publisher")
            content = (
                entry.get("content")[0].get("value") if entry.get("content") else None
            )
            summary = entry.get("summary")

            fe = fg.add_entry(order="append")
            fe.title(title)
            fe.link(href=link)
            fe.author({"name": author_name})
            fe.id(unique_id)
            fe.content(content, type="html")
            fe.updated(updated)
            fe.pubDate(pubdate)
            fe.summary(summary, type="html")

            for enclosure in entry.get("enclosures", []):
                fe.enclosure(
                    url=enclosure.get("href"),
                    type=enclosure.get("type"),
                    length=enclosure.get("length"),
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
    pi = etree.ProcessingInstruction(
        "xml-stylesheet", 'type="text/xsl" href="/static/rss.xsl"'
    )
    root.addprevious(pi)
    atom_string_with_pi = etree.tostring(
        tree, pretty_print=True, xml_declaration=True, encoding="utf-8"
    ).decode()

    return atom_string_with_pi


ATOM_NS = "http://www.w3.org/2005/Atom"
ENTRY_ID = f"{{{ATOM_NS}}}id"
ENTRY_PUBLISHED = f"{{{ATOM_NS}}}published"
ENTRY_UPDATED = f"{{{ATOM_NS}}}updated"


class FeedMerger:
    def __init__(self, feed_name, feed_files):
        self.feed_name = feed_name
        self.feed_files = feed_files
        self.output_dir = os.path.join(settings.DATA_FOLDER, "feeds")
        self.output_file = check_file_path(self.output_dir, f"{feed_name}.xml")
        self.processed_entries = set()

    def merge_feeds(self):
        os.makedirs(self.output_dir, exist_ok=True)
        self._write_feed_header()

        for feed_file in self.feed_files:
            if not os.path.exists(feed_file):
                logging.warning(f"{feed_file} does not exist, skipping")
                continue

            self._process_feed_file(feed_file)

        self._write_feed_footer()

    def _write_feed_header(self):
        with open(self.output_file, "wb") as f:
            f.write(b'<?xml version="1.0" encoding="utf-8"?>\n')
            f.write(b'<?xml-stylesheet type="text/xsl" href="/static/rss.xsl"?>\n')
            f.write(f'<feed xmlns="{ATOM_NS}">\n'.encode("utf-8"))
            f.write(
                f"<title>Translated Feeds for {self.feed_name} | RSS Translator</title>\n".encode(
                    "utf-8"
                )
            )
            f.write(b'<link href="https://rsstranslator.com"/>\n')
            f.write(
                f"<updated>{datetime.now(timezone.utc).isoformat()}</updated>\n".encode(
                    "utf-8"
                )
            )

    def _process_feed_file(self, feed_file):
        try:
            feed_tree = etree.parse(feed_file)
            feed_root = feed_tree.getroot()
            feed_title = feed_root.findtext(f"{{{ATOM_NS}}}title", "")
            feed_url = feed_root.find(f"{{{ATOM_NS}}}link").get("href", "")
            self.processed_entries.update(
                entry.find(ENTRY_ID).text
                for entry in feed_root.iterfind(f"{{{ATOM_NS}}}entry")
                if self._should_process_entry(entry, feed_title, feed_url)
            )

        except Exception as e:
            logging.error(f"FeedMerger::_process_feed_file: {feed_file}: {e}")

    def _should_process_entry(self, entry, feed_title, feed_url):
        try:
            id_elem = entry.find(ENTRY_ID)
            if id_elem is None or id_elem.text in self.processed_entries:
                return False

            published_elem = entry.find(ENTRY_PUBLISHED) or entry.find(ENTRY_UPDATED)
            if published_elem is None:
                return False

            published_date = self._parse_date(published_elem.text)
            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

            if published_date < thirty_days_ago.date():
                return False

            self._add_author_info(entry, feed_title, feed_url)
            self._write_entry(entry)
            return True
        except Exception as e:
            logging.error(f"FeedMerger::_should_process_entry:{e}")
            return False

    def _parse_date(self, date_str):
        try:
            return datetime.fromisoformat(date_str).date()
        except ValueError:
            logging.error(f"Error parsing date: {date_str}")
            return None

    def _add_author_info(self, entry, feed_title, feed_url):
        author_elem = entry.find(f"{{{ATOM_NS}}}author")
        if author_elem is None:
            author_elem = etree.Element(f"{{{ATOM_NS}}}author")
            entry.append(author_elem)

        name_elem = author_elem.find(f"{{{ATOM_NS}}}name")
        if name_elem is None:
            name_elem = etree.SubElement(author_elem, f"{{{ATOM_NS}}}name")

        # 将name元素的文本修改为feed_title+原author信息
        if name_elem.text:
            name_elem.text = f"{feed_title} - {name_elem.text}"
        else:
            name_elem.text = feed_title

        uri_elem = author_elem.find(f"{{{ATOM_NS}}}uri")
        if uri_elem is None:
            uri_elem = etree.SubElement(author_elem, f"{{{ATOM_NS}}}uri")
        uri_elem.text = feed_url

    def _write_entry(self, entry):
        with open(os.path.normpath(self.output_file), "ab") as f:
            f.write(etree.tostring(entry, pretty_print=True))

    def _write_feed_footer(self):
        with open(os.path.normpath(self.output_file), "ab") as f:
            f.write(b"</feed>")
    
def check_file_path(base_path:str, filename:str) -> str:
    fullpath = os.path.normpath(os.path.join(base_path, filename))
    if not fullpath.startswith(base_path):
        raise Exception("not allowed")
    return fullpath


def merge_all_atom(feed_files, feed_name):
    merger = FeedMerger(feed_name, feed_files)
    merger.merge_feeds()


"""
def merge_all_atom(feed_files: list, filename: str):
    ATOM_NS = "http://www.w3.org/2005/Atom"

    output_dir = os.path.join(settings.DATA_FOLDER, "feeds")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{filename}.xml")
    
    with open(os.path.normpath(output_file), "wb") as f:
        # Write Feed Header
        f.write(b'<?xml version="1.0" encoding="utf-8"?>\n')
        f.write(b'<?xml-stylesheet type="text/xsl" href="/static/rss.xsl"?>\n')
        f.write(f'<feed xmlns="{ATOM_NS}">\n'.encode("utf-8"))
        f.write(
            f"<title>Translated Feeds for {filename} | RSS Translator</title>\n".encode(
                "utf-8"
            )
        )
        f.write(b'<link href="https://rsstranslator.com"/>\n')
        f.write(
            f"<updated>{datetime.now(timezone.utc).isoformat()}</updated>\n".encode(
                "utf-8"
            )
        )

        today = date.today()
        thirty_days_ago = today - timedelta(days=30)
        processed_entries = set()

        for feed_file in feed_files:
            if not os.path.exists(feed_file):
                logging.warning(f"{feed_file} does not exist, skipping")
                continue
            
            try:
                feed_tree = etree.parse(feed_file)
                feed_root = feed_tree.getroot()
                
                feed_title = feed_root.findtext(f"{{{ATOM_NS}}}title", "")
                feed_url = feed_root.findtext(f"{{{ATOM_NS}}}link[@rel='self']/@href", "")

                processed_entries.update(
                    {
                        entry.find(f"{{{ATOM_NS}}}id").text
                        for entry in feed_root.xpath(f".//{{{ATOM_NS}}}entry")
                        if _should_process_entry(entry, feed_title, feed_url)
                    }
                )
            except Exception as e:
                logging.error(f"Error processing {feed_file}: {e}")
            
            # for _, entry in etree.iterparse(
            #     feed_file, events=("end",), tag=f"{{{ATOM_NS}}}entry"
            # ):
            def _should_process_entry(entry, feed_title, feed_url):
                id_elem = entry.find(f"{{{ATOM_NS}}}id")
                if id_elem is None and id_elem.text in processed_entries:
                    return False

                published_elem = entry.find(
                    f"{{{ATOM_NS}}}published"
                ) or entry.find(f"{{{ATOM_NS}}}updated")
                if published_elem is None:
                    return False

                published_date = parser.parse(published_elem.text).date()
                if published_date < thirty_days_ago.date():
                    return False
                    
                author_elem = etree.Element(f"{{{ATOM_NS}}}author")
                name_elem = etree.SubElement(author_elem, f"{{{ATOM_NS}}}name")
                name_elem.text = feed_title
                uri_elem = etree.SubElement(author_elem, f"{{{ATOM_NS}}}uri")
                uri_elem.text = feed_url
                entry.append(author_elem)

                f.write(etree.tostring(entry, pretty_print=True))
                return True

        f.write(b"</feed>")
"""

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
