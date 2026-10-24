from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from . import api

router = DefaultRouter()
router.register("panden", api.PandViewSet, basename="pand")
router.register("buurten", api.BuurtViewSet, basename="buurt")
router.register("projecten", api.ProjectViewSet, basename="project")

urlpatterns = [
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    *router.urls,
]
