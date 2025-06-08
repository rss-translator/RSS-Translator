import logging
import os
import json

from django.conf import settings
from django.http import HttpResponse, StreamingHttpResponse, JsonResponse
from django.utils.encoding import smart_str
from django.views.decorators.cache import cache_page
from django.views.decorators.http import condition
from .models import Feed
from django.shortcuts import redirect, render
from django.contrib import messages
from django.core.files.uploadedfile import InMemoryUploadedFile
from opyml import OPML
from django.utils.translation import gettext_lazy as _
from utils.feed_action import merge_all_atom, check_file_path
# from django.utils.http import url_has_allowed_host_and_scheme
# from django.core.paginator import Paginator

from utils.modelAdmin_utils import (
    get_translator_models,
    status_icon,
)
# from .custom_admin_site import core_admin_site

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

def get_modified(request, feed_slug):
    try:
        modified = Feed.objects.get(slug=feed_slug).last_translate
    except Feed.DoesNotExist:
        logging.warning(
            "Translated feed not found, Maybe still in progress, Please confirm it's exist: %s",
            feed_slug,
        )
        modified = None
    return modified


def get_etag(request, feed_slug):
    try:
        modified = Feed.objects.get(slug=feed_slug).etag
    except Feed.DoesNotExist:
        logging.warning(
            "Translated feed not found, Maybe still in progress, Please confirm it's exist: %s",
            feed_slug,
        )
        modified = None
    return modified.strftime("%Y-%m-%d %H:%M:%S") if modified else None

# @cache_page(60 * 15)  # Cache this view for 15 minutes
@condition(etag_func=get_etag, last_modified_func=get_modified)
def rss(request, feed_slug, type="t"):
    # Sanitize the feed_slug to prevent path traversal attacks
    feed_slug = smart_str(feed_slug)

    #feed_file_path = os.path.join(settings.DATA_FOLDER, "feeds", f"{feed_slug}.xml")
    base_path = os.path.join(settings.DATA_FOLDER, "feeds")
    feed_file_path = check_file_path(base_path=base_path, filename=f"{type}_{feed_slug}.xml")
    # Check if the file exists and if not, raise a 404 error
    if not os.path.exists(feed_file_path):
        logging.warning("Requested feed file not found: %s", feed_file_path)
        # raise Http404(f"The feed with ID {feed_slug} does not exist.")
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
def rss_json(request, feed_slug):
    # Sanitize the feed_slug to prevent path traversal attacks
    feed_slug = smart_str(feed_slug)
    base_path = os.path.join(settings.DATA_FOLDER, "feeds")
    feed_file_path = check_file_path(base_path, f"t_{feed_slug}.json")
    content_type = "application/json; charset=utf-8"

    # Check if the file exists and if not, raise a 404 error
    if not os.path.exists(feed_file_path):
        logging.warning("Requested feed file not found: %s", feed_file_path)
        # raise Http404(f"The feed with ID {feed_slug} does not exist.")
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


def get_feed_file_paths(feeds: list, type: str = "o") -> list:
    feed_file_dir = os.path.abspath(os.path.join(settings.DATA_FOLDER, "feeds"))
    feed_file_paths = []

    for feed in feeds:
        file_path = os.path.abspath(
            os.path.join(feed_file_dir, f"{type}_{feed.slug}.xml")
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


# def translator_list_view(request):
#     page_number = int(request.GET.get("p", 1))
#     paginator = TranslatorPaginator()
#     page = paginator.get_page(page_number)
#     page_range = paginator.get_elided_page_range(page_number, on_each_side=2, on_ends=2)

#     context = {
#         **core_admin_site.each_context(request),
#         "title": "Translator",
#         "page": page,
#         "page_range": page_range,
#         "translators": page.object_list,
#     }
#     return render(request, "admin/translator.html", context)


# def translator_add_view(request):
#     if request.method == "POST":
#         translator_name = request.POST.get("translator_name", "/")
#         # redirect to example.com/translator/translator_name/add
#         target = f"/core/{translator_name}/add"
#         return (
#             redirect(target)
#             if url_has_allowed_host_and_scheme(target, allowed_hosts=None)
#             else redirect("/")
#         )
#     else:
#         models = get_translator_models()
#         translator_list = []
#         for model in models:
#             translator_list.append(
#                 {
#                     "table_name": model._meta.db_table.split("_")[1],
#                     "provider": model._meta.verbose_name,
#                 }
#             )
#         context = {
#             **core_admin_site.each_context(request),
#             "translator_choices": translator_list,
#         }
#         return render(request, "admin/translator_add.html", context)


# class TranslatorPaginator(Paginator):
#     def __init__(self):
#         super().__init__(self, 100)

#         self.translator_count = 3

#     @property
#     def count(self):
#         return self.translator_count

#     def page(self, number):
#         limit = self.per_page
#         offset = (number - 1) * self.per_page
#         return self._get_page(
#             self.enqueued_items(limit, offset),
#             number,
#             self,
#         )

#     # Copied from Huey's SqliteStorage with some modifications to allow pagination
#     def enqueued_items(self, limit, offset):
#         translator_models = get_translator_models()
#         translator_list = []
#         for model in translator_models:
#             objects = (
#                 model.objects.all()
#                 .order_by("name")
#                 .values_list("id", "name", "valid")[offset : offset + limit]
#             )
#             for obj_id, obj_name, obj_valid in objects:
#                 translator_list.append(
#                     {
#                         "id": obj_id,
#                         "table_name": model._meta.db_table.split("_")[1],
#                         "name": obj_name,
#                         "valid": status_icon(obj_valid),
#                         "provider": model._meta.verbose_name,
#                     }
#                 )

#         return translator_list
