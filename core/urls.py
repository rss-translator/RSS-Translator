from django.urls import path

from . import views

app_name = "core"
urlpatterns = [
    # path("filter/<str:name>", views.filter, name="filter"),
    # path("all/<str:name>", views.all, name="all"),
    # path("all/<str:name>/", views.all, name="all"),
    path("category/proxy/<str:category>", views.category_rss, kwargs={"type": "o"}, name="category"),
    path("category/proxy/<str:category>/", views.category_rss, kwargs={"type": "o"}, name="category"),
    path("category/rss/<str:category>", views.category_rss, kwargs={"type": "t"}, name="category"),
    path("category/rss/<str:category>/", views.category_rss, kwargs={"type": "t"}, name="category"),
    path("category/json/<str:category>", views.category_json, kwargs={"type": "t"}, name="category"),
    path("category/json/<str:category>/", views.category_json, kwargs={"type": "t"}, name="category"),
    path("rss/<str:feed_slug>", views.rss, kwargs={"type": "t"}, name="rss"),
    path("rss/<str:feed_slug>/", views.rss, kwargs={"type": "t"}, name="rss"),
    path("json/<str:feed_slug>", views.rss_json, name="json"),
    path("json/<str:feed_slug>/", views.rss_json, name="json"),
    path('import_opml/', views.import_opml, name='import_opml'),
    path("proxy/<str:feed_slug>", views.rss, kwargs={"type": "o"}, name="proxy"),
    path("proxy/<str:feed_slug>/", views.rss, kwargs={"type": "o"}, name="proxy"),
]
