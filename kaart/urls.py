from django.urls import path

from . import tiles, views

app_name = "kaart"

urlpatterns = [
    path("", views.home, name="home"),
    path("tekeningen/langzaam/", views.tekeningen_langzaam, name="tekeningen_langzaam"),
    path("tekeningen/snel/", views.tekeningen_snel, name="tekeningen_snel"),
    path("projecten/", views.projecten_overzicht, name="projecten_overzicht"),
    path("kaart/", views.kaart_tekenen, name="kaart"),
    path("tiles/panden/<int:z>/<int:x>/<int:y>.pbf", tiles.panden_tile, name="tile_panden"),
    path("p/", views.ProjectLijst.as_view(), name="project_lijst"),
    path("p/nieuw/", views.ProjectNieuw.as_view(), name="project_nieuw"),
    path("p/<int:pk>/", views.ProjectDetail.as_view(), name="project_detail"),
    path("p/<int:pk>/bewerken/", views.ProjectBewerk.as_view(), name="project_bewerk"),
]
