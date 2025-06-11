import logging
import os
import json

from django.conf import settings
from django.http import HttpResponse, StreamingHttpResponse, JsonResponse
from django.utils.encoding import smart_str
from django.views.decorators.cache import cache_page
from django.views.decorators.http import condition
from .models import Feed
from django.shortcuts import redirect
from django.contrib import messages
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.cache import cache
from functools import wraps

from opyml import OPML
from feed2json import feed2json
from django.utils.translation import gettext_lazy as _

from utils.feed_action import merge_all_atom, generate_atom_feed

def import_opml(request):
    if request.method == 'POST':
        opml_file = request.FILES.get('opml_file')
        if opml_file and isinstance(opml_file, InMemoryUploadedFile):
            try:
                opml_content = opml_file.read().decode('utf-8')
                opml = OPML.from_xml(opml_content)
                
                for outline in opml.body.outlines:
                    category = outline.text
                    #category, _ = Category.objects.get_or_create(name=category_name)
                    
                    for feed in outline.outlines:
                        Feed.objects.create(
                            name=feed.title or feed.text,
                            feed_url=feed.xml_url,
                            category=category
                        )
                
                messages.success(request, _("OPML file imported successfully."))
            except Exception as e:
                messages.error(request, _("Error importing OPML file: {}").format(str(e)))
        else:
            messages.error(request, _("Please upload a valid OPML file."))
    
    return redirect('admin:core_feed_changelist')

def get_modified(request, feed_slug, type="t"):
    try:
        if type == "t":
            modified = Feed.objects.get(slug=feed_slug).last_translate
        else:
            modified = Feed.objects.get(slug=feed_slug).last_fetch
    except Feed.DoesNotExist:
        logging.warning(
            "Translated feed not found, Maybe still in progress, Please confirm it's exist: %s",
            feed_slug,
        )
        modified = None
    return modified


def get_etag(request, feed_slug, type="t"):
    try:
        if type == "t":
            etag = Feed.objects.get(slug=feed_slug).last_translate
        else:
            etag = Feed.objects.get(slug=feed_slug).etag
    except Feed.DoesNotExist:
        logging.warning(
            "Feed not fetched yet, Please update it first: %s",
            feed_slug,
        )
        etag = None
    return etag

def get_feed_cache_timeout(request, feed_slug, *args, **kwargs):
    """
    根据 feed 的 update_frequency 获取缓存超时时间（秒）
    """    
    try:
        feed = Feed.objects.get(slug=feed_slug)
        # 将分钟转换为秒，并确保至少缓存1分钟
        return max(60, feed.update_frequency * 60)
    except Feed.DoesNotExist:
        # 如果找不到 feed，返回默认缓存时间（15分钟）
        return 60 * 15


def dynamic_cache_page(timeout_func):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            view_name = view_func.__name__
            feed_slug = kwargs.get("feed_slug")
            feed_type = kwargs.get("type", "t")
            # 计算动态超时时间
            timeout = timeout_func(request, *args, **kwargs)
            # 生成唯一的缓存键
            cache_key = f'view_cache_{view_name}_{feed_slug}_{feed_type}'
            # 尝试从缓存获取响应
            response = cache.get(cache_key)
            if response is None:
                # 缓存未命中，调用视图函数
                logging.debug(f"Cache MISS for key: {cache_key}")
                response = view_func(request, *args, **kwargs)
                # 缓存响应
                cache.set(cache_key, response, timeout)
                logging.debug(f"Cached response for key: {cache_key} with timeout: {timeout}s")
            else:
                logging.debug(f"Cache HIT for key: {cache_key}")
            return response
        return _wrapped_view
    return decorator


@dynamic_cache_page(get_feed_cache_timeout)
@condition(etag_func=get_etag, last_modified_func=get_modified)
def rss(request, feed_slug, type="t"):
    # Sanitize the feed_slug to prevent path traversal attacks
    feed_slug = smart_str(feed_slug)
    try:
        feed = Feed.objects.get(slug=feed_slug)
        atom_feed = generate_atom_feed(feed, type)
        if not atom_feed:
            return HttpResponse(status=500, content="Feed not found, Maybe it's still in progress")
        response = StreamingHttpResponse(
            atom_feed, content_type="application/xml"
        )   
        response["Content-Disposition"] = "inline; filename=feed.xml"
        return response
    except Feed.DoesNotExist:
        logging.warning(f"Requested feed not found: {feed_slug}")
        return HttpResponse(status=404, content=f"Feed {feed_slug} not found")
    except Exception as e:
        logging.error(f"Error generating rss {feed_slug}: {str(e)}")
        return HttpResponse(status=500, content="Internal Server Error")


@dynamic_cache_page(get_feed_cache_timeout)
@condition(etag_func=get_etag, last_modified_func=get_modified)
def rss_json(request, feed_slug, type="t"):
    feed_slug = smart_str(feed_slug)
    try:
        feed = Feed.objects.get(slug=feed_slug)
        atom_feed = generate_atom_feed(feed, type)
        if not atom_feed:
            return HttpResponse(status=500, content="Feed not found, Maybe it's still in progress")
        feed_json = feed2json(atom_feed)
        return JsonResponse(feed_json)
    except Feed.DoesNotExist:
        logging.warning(f"Requested feed not found: {feed_slug}")
        return HttpResponse(status=404, content=f"Feed {feed_slug} not found")
    except Exception as e:
        logging.error(f"Error generating json {feed_slug}: {str(e)}")
        return HttpResponse(status=500, content="Internal Server Error")


@cache_page(60 * 15)  # Cache this view for 15 minutes
def all(request, name):
    if name != "t":
        return HttpResponse(status=404)
    try:
        # get all data from Feed
        feeds = Feed.objects.all()
        # get all feed file path from feeds.slug
        feed_file_paths = get_feed_file_paths(feeds, "t")
        merge_all_atom(feed_file_paths, "all_t")
        base_path = os.path.join(settings.DATA_FOLDER, "feeds")
        #merge_file_path = os.path.join(settings.DATA_FOLDER, "feeds", "all_t.xml")
        merge_file_path = check_file_path(base_path, "all_t.xml")
        response = StreamingHttpResponse(
            file_iterator(merge_file_path), content_type="application/xml"
        )
        response["Content-Disposition"] = "inline; filename=all_t.xml"
        logging.info("All Translated Feed file served: %s", merge_file_path)
        return response
    except Exception as e:
        # Log the exception and return an appropriate error response
        logging.exception(
            "Failed to read the all_t feed file: %s / %s", merge_file_path, str(e)
        )
        return HttpResponse(status=500)


@cache_page(60 * 15)  # Cache this view for 15 minutes
def category(request, category: str):
    all_category = Feed.category.tag_model.objects.all()

    if category not in all_category:
        return HttpResponse(status=404)

    try:
        # # get all data from Feed
        feeds = Feed.objects.filter(feed__category__name=category)
        # # get all feed file path from feeds.slug
        # feed_file_paths = [os.path.join(settings.DATA_FOLDER, 'feeds', f'{feed.slug}.xml') for feed in feeds]
        feed_file_paths = get_feed_file_paths(feeds, "t")
        merge_all_atom(feed_file_paths, category)
        base_path = os.path.join(settings.DATA_FOLDER, "feeds")
        #merge_file_path = os.path.join(settings.DATA_FOLDER, "feeds", f"{category}.xml")
        merge_file_path = check_file_path(base_path, f"{category}.xml")
        response = StreamingHttpResponse( 
            file_iterator(merge_file_path), content_type="application/xml"
        )
        response["Content-Disposition"] = f"inline; filename={category}.xml"
        logging.info("Category Feed file served: %s", merge_file_path)
        return response
    except Exception as e:
        # Log the exception and return an appropriate error response
        logging.exception(
            "Failed to read the category feed file: %s / %s", category, str(e)
        )
        return HttpResponse(status=500)


# def get_feed_file_paths(feeds: list, type: str = "o") -> list:
#     feed_file_dir = os.path.abspath(os.path.join(settings.DATA_FOLDER, "feeds"))
#     feed_file_paths = []

#     for feed in feeds:
#         file_path = os.path.abspath(
#             os.path.join(feed_file_dir, f"{type}_{feed.slug}.xml")
#         )  # 获取绝对路径
#         if (
#             os.path.commonpath((feed_file_dir, file_path)) != feed_file_dir
#         ):  # 对比最长公共路径，防止目录遍历
#             raise ValueError(f"Invalid feed file path: {file_path}")
#         feed_file_paths.append(file_path)
#     return feed_file_paths


def file_iterator(file_path, chunk_size=8192):
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk
