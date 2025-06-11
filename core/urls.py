from django.urls import path

from . import views

app_name = "core"
urlpatterns = [
    # path("filter/<str:name>", views.filter, name="filter"),
    # path("all/<str:name>", views.all, name="all"),
    # path("all/<str:name>/", views.all, name="all"),
    path("category/<str:category>", views.category, name="category"),
    path("category/<str:category>/", views.category, name="category"),
    path("rss/<str:feed_slug>", views.rss, kwargs={"type": "t"}),
    path("rss/<str:feed_slug>/", views.rss, kwargs={"type": "t"}),
    path("json/<str:feed_slug>", views.rss_json, name="json"),
    path("json/<str:feed_slug>/", views.rss_json, name="json"),
    path('import_opml/', views.import_opml, name='import_opml'),
    path("proxy/<str:feed_slug>", views.rss, kwargs={"type": "o"}),
    path("proxy/<str:feed_slug>/", views.rss, kwargs={"type": "o"}),
]
