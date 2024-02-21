from django.urls import path

from . import views

app_name = "core"
urlpatterns = [
    path("log/", views.log, name="log"),
    path("<str:feed_sid>/", views.rss, name="rss"),
]
