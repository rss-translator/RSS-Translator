from django.urls import path

from . import views
# from django.urls import re_path

app_name = "core"
urlpatterns = [
    # path("filter/<str:name>", views.filter, name="filter"),
    # path("translator/add", views.translator_add_view, name="translator_add"),
    # path("translator/list", views.translator_list_view, name="translator_list"),
    path("all/<str:name>", views.all, name="all"),
    path("all/<str:name>/", views.all, name="all"),
    path("category/<str:category>", views.category, name="category"),
    path("category/<str:category>/", views.category, name="category"),
    path("json/<str:feed_slug>", views.rss_json, name="json"),
    path("json/<str:feed_slug>/", views.rss_json, name="json"),
    path('feed/import_opml/', views.import_opml, name='import_opml'),
    path("proxy/<str:feed_slug>", views.rss, kwargs={"type": "o"}, name="proxy"),
    path("proxy/<str:feed_slug>/", views.rss, kwargs={"type": "o"}, name="proxy"),
    # re_path(r"(?P<feed_slug>[^/]+)/?$", views.rss, type="t", name="rss"),
    path("<str:feed_slug>/", views.rss, kwargs={"type": "t"}, name="rss"),
    path("<str:feed_slug>", views.rss, kwargs={"type": "t"}, name="rss"),
]
