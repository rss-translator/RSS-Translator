from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _

class CoreAdminSite(AdminSite):
    site_header = _("RSS Translator Admin")
    site_title = _("RSS Translator")
    index_title = _("Dashboard")

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)
        if app_list and app_list[0]["app_label"] == "core":
            engine = {"models": [
                        {
                            "name": _("Translator"),
                            "object_name": "Translator",
                            "admin_url": "/core/translator/list",
                            "add_url": "/core/translator/add",
                            # "view_only": False,
                    }
                ],
            }
            app_list[0]["models"].extend(engine["models"])
        return app_list

core_admin_site = CoreAdminSite()

