import logging
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
from lxml import etree
from feed2json import feed2json
import xml.etree.ElementTree as ET
from django.utils.translation import gettext_lazy as _

from utils.feed_action import merge_feeds_into_one_atom, generate_atom_feed

def import_opml(request):
    if request.method == 'POST':
        opml_file = request.FILES.get('opml_file')
        if opml_file and isinstance(opml_file, InMemoryUploadedFile):
            try:
                # 直接读取字节数据（lxml 支持二进制解析）
                opml_content = opml_file.read()
                
                # 使用 lxml 解析 OPML
                root = etree.fromstring(opml_content)
                body = root.find('body')
                
                if body is None:
                    messages.error(request, _("Invalid OPML: Missing body element"))
                    return redirect('admin:core_feed_changelist')
                
                # 递归处理所有 outline 节点
                def process_outlines(outlines, category=None):
                    for outline in outlines:
                        # 检查是否为 feed（有 xmlUrl 属性）
                        if 'xmlUrl' in outline.attrib:
                            Feed.objects.create(
                                name=outline.get('title') or outline.get('text'),
                                feed_url=outline.get('xmlUrl'),
                                category=category
                            )
                        # 处理嵌套结构（新类别）
                        elif outline.find('outline') is not None:
                            new_category = outline.get('text') or outline.get('title')
                            process_outlines(outline.findall('outline'), new_category)
                
                # 从 body 开始处理顶级 outline
                process_outlines(body.findall('outline'))
                
                messages.success(request, _("OPML file imported successfully."))
            except etree.XMLSyntaxError as e:
                messages.error(request, _("XML syntax error: {}").format(str(e)))
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
def category_rss(request, category: str, type="t"):
    category = smart_str(category)
    all_category = Feed.category.tag_model.objects.all()

    if category not in all_category:
        return HttpResponse(status=404)

    try:
        # get all data from Feed
        feeds = Feed.objects.filter(category__name=category)
        atom_feed = merge_feeds_into_one_atom(category, feeds, type)
        if not atom_feed:
            return HttpResponse(status=500, content="No category feed found")
        response = StreamingHttpResponse(
            atom_feed, content_type="application/xml"
        )   
        response["Content-Disposition"] = f"inline; filename=feed_{category}.xml"
        return response
    except Exception as e:
        logging.exception("Failed to read the category feeds: %s / %s", category, str(e))
        return HttpResponse(status=500, content="Internal Server Error")

@cache_page(60 * 15)  # Cache this view for 15 minutes
def category_json(request, category: str, type="t"):
    category = smart_str(category)
    all_category = Feed.category.tag_model.objects.all()

    if category not in all_category:
        return HttpResponse(status=404)

    try:
        # get all data from Feed
        feeds = Feed.objects.filter(category__name=category)
        atom_feed = merge_feeds_into_one_atom(category, feeds, type)
        if not atom_feed:
            return HttpResponse(status=500, content="No category feeds found")
        feed_json = feed2json(atom_feed)
        return JsonResponse(feed_json)
    except Exception as e:
        logging.exception("Failed to load the category feeds: %s / %s", category, str(e))
        return HttpResponse(status=500, content="Internal Server Error")
