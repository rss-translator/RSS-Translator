from urllib.parse import urljoin

import feedparser
import json
import requests
from bs4 import BeautifulSoup


def main(context):
    payload = json.loads(context.req.body) if context.req.body else {}
    url = payload.get("url")
    if not url:
        return context.res.json({"error": "url is required"})

    rss_links = get_page_rss(url)
    result = {
        "total": len(rss_links),
        "rss_links": rss_links,
    }
    context.log(result)
    return context.res.json(result)


def handle_url(url, base_url):
    return urljoin(base_url, url)


def is_valid_feed(url):
    feed = feedparser.parse(url)
    return hasattr(feed, "version") and feed.version != ""


def get_page_rss(url):
    page_rss = []
    unique = set()
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    default_title = soup.title.string if soup.title else ""

    types = [
        "application/rss+xml",
        "application/atom+xml",
        "application/rdf+xml",
        "application/rss",
        "application/atom",
        "application/rdf",
        "text/rss+xml",
        "text/atom+xml",
        "text/rdf+xml",
        "text/rss",
        "text/atom",
        "text/rdf",
        "application/feed+json",
    ]

    # links
    for link in soup.find_all("link"):
        if link.has_attr("type") and link["type"] in types:
            feed_url = link.get("href")
            if feed_url and is_valid_feed(feed_url):
                feed = {
                    "url": handle_url(feed_url, url),
                    "title": link.get("title", default_title),
                }
                if feed["url"] not in unique:
                    page_rss.append(feed)
                    unique.add(feed["url"])

    # a
    for a in soup.find_all("a"):
        href = a.get("href")
        if href and ("/feed" in href or "/rss" in href or "/atom" in href):
            feed = {
                "url": handle_url(href, url),
                "title": a.string or a.get("title", default_title),
            }
            if feed["url"] not in unique and is_valid_feed(feed["url"]):
                page_rss.append(feed)
                unique.add(feed["url"])

    return page_rss
