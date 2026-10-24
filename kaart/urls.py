from django.urls import path

from . import views

app_name = "kaart"

urlpatterns = [
    path("", views.home, name="home"),
    path("tekeningen/langzaam/", views.tekeningen_langzaam, name="tekeningen_langzaam"),
    path("tekeningen/snel/", views.tekeningen_snel, name="tekeningen_snel"),
    path("projecten/", views.projecten_overzicht, name="projecten_overzicht"),
]
