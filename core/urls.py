from django.urls import path

from . import views
from django.urls import re_path

app_name = "core"
urlpatterns = [
    #path("<str:feed_sid>/", views.rss, name="rss"),
    re_path(r'(?P<feed_sid>[^/]+)/?$', views.rss, name='rss'),
]
