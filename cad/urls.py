from django.urls import path

from . import views

app_name = "cad"

urlpatterns = [
    path("upload/", views.upload, name="upload"),
    path("tekening/<int:pk>/", views.tekening, name="tekening"),
    path("api/tekening/<int:pk>/ruimtes/", views.ruimtes_geojson, name="ruimtes"),
    path("api/tekening/<int:pk>/fouten/", views.fouten_geojson, name="fouten"),
]
