from django.urls import path

from . import views
from django.urls import re_path

app_name = "core"
urlpatterns = [
    # path("filter/<str:name>", views.filter, name="filter"),
    path("all/<str:name>", views.all, name="all"),
    path("all/<str:name>/", views.all, name="all"),
    path("category/<str:category>", views.category, name="category"),
    path("category/<str:category>/", views.category, name="category"),
    path("json/<str:feed_sid>", views.rss_json, name="json"),
    path("json/<str:feed_sid>/", views.rss_json, name="json"),
    path('core/feed/import_opml/', views.import_opml, name='import_opml'),
    re_path(r"(?P<feed_sid>[^/]+)/?$", views.rss, name="rss"),
]
