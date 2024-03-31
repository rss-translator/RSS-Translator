from django.urls import path

from . import views
from django.urls import re_path

app_name = "core"
urlpatterns = [
    #path("filter/<str:name>", views.filter, name="filter"),
    path("all/<str:name>", views.all, name="all"),
    path("all/<str:name>/", views.all, name="all"),
    re_path(r'(?P<feed_sid>[^/]+)/?$', views.rss, name='rss'),
]
