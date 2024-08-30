import logging
import os
import json

from django.conf import settings
from django.http import HttpResponse, StreamingHttpResponse, JsonResponse
from django.utils.encoding import smart_str
from django.views.decorators.cache import cache_page
from django.views.decorators.http import condition
from .models import T_Feed, O_Feed
from django.shortcuts import redirect
from django.contrib import messages
from django.core.files.uploadedfile import InMemoryUploadedFile
from opyml import OPML
from django.utils.translation import gettext_lazy as _

from utils.feed_action import merge_all_atom, check_file_path

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
                        O_Feed.objects.create(
                            name=feed.title or feed.text,
                            feed_url=feed.xml_url,
                            category=category
                        )
                
                messages.success(request, _("OPML file imported successfully."))
            except Exception as e:
                messages.error(request, _("Error importing OPML file: {}").format(str(e)))
        else:
            messages.error(request, _("Please upload a valid OPML file."))
    
    return redirect('admin:core_o_feed_changelist')

def get_modified(request, feed_sid):
    try:
        modified = T_Feed.objects.get(sid=feed_sid).modified
    except T_Feed.DoesNotExist:
        logging.warning(
            "Translated feed not found, Maybe still in progress, Please confirm it's exist: %s",
            feed_sid,
        )
        modified = None
    return modified


def get_etag(request, feed_sid):
    try:
        modified = T_Feed.objects.get(sid=feed_sid).modified
    except T_Feed.DoesNotExist:
        logging.warning(
            "Translated feed not found, Maybe still in progress, Please confirm it's exist: %s",
            feed_sid,
        )
        modified = None
    return modified.strftime("%Y-%m-%d %H:%M:%S") if modified else None


# @cache_page(60 * 15)  # Cache this view for 15 minutes
@condition(etag_func=get_etag, last_modified_func=get_modified)
def rss(request, feed_sid):
    # Sanitize the feed_sid to prevent path traversal attacks
    feed_sid = smart_str(feed_sid)

    #feed_file_path = os.path.join(settings.DATA_FOLDER, "feeds", f"{feed_sid}.xml")
    base_path = os.path.join(settings.DATA_FOLDER, "feeds")
    feed_file_path = check_file_path(base_path=base_path, filename=f"{feed_sid}.xml")
    # Check if the file exists and if not, raise a 404 error
    if not os.path.exists(feed_file_path):
        logging.warning("Requested feed file not found: %s", feed_file_path)
        # raise Http404(f"The feed with ID {feed_sid} does not exist.")
        return HttpResponse(
            "Please wait for the translation to complete or check if the original feeds has been verified"
        )

    try:
        # Stream the file content
        # def file_iterator(file_name, chunk_size=8192):
        #     with open(file_name, "rb") as f:
        #         while True:
        #             chunk = f.read(chunk_size)
        #             if not chunk:
        #                 break
        #             yield chunk

        response = StreamingHttpResponse(
            file_iterator(feed_file_path), content_type="application/xml"
        )
        response["Content-Disposition"] = (
            f'inline; filename="{os.path.basename(feed_file_path)}"'
        )
        logging.info("Feed file served: %s", feed_file_path)
        return response
    except IOError as e:
        # Log the exception and return an appropriate error response
        logging.exception(
            "Failed to read the feed file: %s / %s", feed_file_path, str(e)
        )
        return HttpResponse(status=500)


@condition(etag_func=get_etag, last_modified_func=get_modified)
def rss_json(request, feed_sid):
    # Sanitize the feed_sid to prevent path traversal attacks
    feed_sid = smart_str(feed_sid)
    base_path = os.path.join(settings.DATA_FOLDER, "feeds")
    feed_file_path = check_file_path(base_path, f"{feed_sid}.json")
    content_type = "application/json; charset=utf-8"

    # Check if the file exists and if not, raise a 404 error
    if not os.path.exists(feed_file_path):
        logging.warning("Requested feed file not found: %s", feed_file_path)
        # raise Http404(f"The feed with ID {feed_sid} does not exist.")
        return HttpResponse(
            "Please wait for the translation to complete or check if the original feeds has been verified"
        )

    try:
        with open(feed_file_path, "rb") as f:
            feed_data = json.load(f)
        response = JsonResponse(feed_data)

        logging.info("Feed file served: %s", feed_file_path)
        return response
    except Exception as e:
        # Log the exception and return an appropriate error response
        logging.exception(
            "Failed to read the feed file: %s / %s", feed_file_path, str(e)
        )
        return HttpResponse(status=500)


@cache_page(60 * 15)  # Cache this view for 15 minutes
def all(request, name):
    if name != "t":
        return HttpResponse(status=404)
    try:
        # get all data from t_feed
        feeds = T_Feed.objects.all()
        # get all feed file path from feeds.sid
        feed_file_paths = get_feed_file_paths(feeds)
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
    all_category = O_Feed.category.tag_model.objects.all()

    if category not in all_category:
        return HttpResponse(status=404)

    try:
        # # get all data from t_feed
        feeds = T_Feed.objects.filter(o_feed__category__name=category)
        # # get all feed file path from feeds.sid
        # feed_file_paths = [os.path.join(settings.DATA_FOLDER, 'feeds', f'{feed.sid}.xml') for feed in feeds]
        feed_file_paths = get_feed_file_paths(feeds)
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


def get_feed_file_paths(feeds: list) -> list:
    feed_file_dir = os.path.abspath(os.path.join(settings.DATA_FOLDER, "feeds"))
    feed_file_paths = []

    for feed in feeds:
        file_path = os.path.abspath(
            os.path.join(feed_file_dir, f"{feed.sid}.xml")
        )  # 获取绝对路径
        if (
            os.path.commonpath((feed_file_dir, file_path)) != feed_file_dir
        ):  # 对比最长公共路径，防止目录遍历
            raise ValueError(f"Invalid feed file path: {file_path}")
        feed_file_paths.append(file_path)
    return feed_file_paths


def file_iterator(file_path, chunk_size=8192):
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk
