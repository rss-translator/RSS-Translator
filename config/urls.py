"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

import os
from django.urls import path, include
from django.conf import settings
from django.views.generic.base import RedirectView
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from core.admin import core_admin_site
from core import views
favicon_view = RedirectView.as_view(url="/static/favicon.ico", permanent=True)


@login_required
def log(request):
    log_file = os.path.join(settings.DATA_FOLDER, "app.log")
    with open(log_file, "r") as file:
        log_content = file.read()
    return HttpResponse(log_content, content_type="text/plain; charset=utf-8")


if settings.DEMO:
    # from django.contrib import admin
    class AccessUser:
        has_module_perms = has_perm = __getattr__ = lambda s, *a, **kw: True

    core_admin_site.has_permission = lambda r: setattr(r, "user", AccessUser()) or True

urlpatterns = [
    path("favicon.ico", favicon_view),
    path("log/", log, name="log"),
    path("rss/", include("core.urls")),
    path("translator/add", views.translator_add_view, name="translator_add"),
    path("translator/list", views.translator_list_view, name="translator_list"),
    path("", core_admin_site.urls),
]

if settings.DEBUG:
    urlpatterns.insert(1, path("__debug__/", include("debug_toolbar.urls")))
