from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from kaart.health import health

urlpatterns = [
    path("health", health, name="health"),
    path("admin/", admin.site.urls),
    path("api/", include("kaart.api_urls")),
    path("cad/", include("cad.urls")),
    path("", include("kaart.urls")),
]

if settings.DEBUG:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns += debug_toolbar_urls()
