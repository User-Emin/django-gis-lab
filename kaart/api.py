from django_filters import rest_framework as df
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.exceptions import ParseError
from rest_framework_gis.fields import GeometryField
from rest_framework_gis.filters import InBBoxFilter
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from .models import Buurt, Pand, Project

TOEGESTANE_SRID = {4326: "WGS84 (graden, GeoJSON-standaard)", 28992: "RD New (meters)"}

SRID_PARAM = OpenApiParameter(
    "srid",
    OpenApiTypes.INT,
    description="Coördinaatstelsel van de uitvoer én van in_bbox: 4326 (standaard) of 28992.",
    enum=sorted(TOEGESTANE_SRID),
)


def gevraagde_srid(request) -> int:
    """?srid= uit het verzoek; standaard 4326 omdat GeoJSON (RFC 7946) WGS84 is."""
    ruw = request.query_params.get("srid", "4326")
    try:
        srid = int(ruw)
    except ValueError:
        raise ParseError(f"srid moet een getal zijn, kreeg {ruw!r}") from None
    if srid not in TOEGESTANE_SRID:
        raise ParseError(f"srid {srid} niet toegestaan; kies uit {sorted(TOEGESTANE_SRID)}")
    return srid


class SridGeometryField(GeometryField):
    """Zet de geometrie om naar het gevraagde stelsel voordat ze als GeoJSON uitgaat."""

    def to_representation(self, value):
        request = self.context.get("request")
        if value is not None and request is not None:
            srid = gevraagde_srid(request)
            if value.srid != srid:
                value = value.transform(srid, clone=True)
        return super().to_representation(value)


class SridBBoxFilter(InBBoxFilter):
    """InBBoxFilter met bbox in het gevraagde stelsel en keuze contained/overlap.

    ?in_bbox=minx,miny,maxx,maxy  (zelfde stelsel als ?srid=)
    ?bbox_modus=overlap           (bboverlaps i.p.v. contained)
    """

    def get_filter_bbox(self, request):
        bbox = super().get_filter_bbox(request)
        if bbox is not None:
            bbox.srid = gevraagde_srid(request)
        return bbox

    def filter_queryset(self, request, queryset, view):
        modus = request.query_params.get("bbox_modus", "contained")
        if modus not in ("contained", "overlap"):
            raise ParseError("bbox_modus is 'contained' of 'overlap'")
        view.bbox_filter_include_overlapping = modus == "overlap"
        return super().filter_queryset(request, queryset, view)

    def get_schema_operation_parameters(self, view):
        params = super().get_schema_operation_parameters(view)
        params[0]["description"] = "Bounding box minx,miny,maxx,maxy in het stelsel van ?srid="
        params.append(
            {
                "name": "bbox_modus",
                "required": False,
                "in": "query",
                "description": (
                    "contained (standaard): bbox van het object volledig binnen; "
                    "overlap: bboxen overlappen"
                ),
                "schema": {"type": "string", "enum": ["contained", "overlap"]},
            }
        )
        return params


class PandSerializer(GeoFeatureModelSerializer):
    geom = SridGeometryField()

    class Meta:
        model = Pand
        geo_field = "geom"
        fields = ["id", "identificatie", "bouwjaar", "status", "gebruiksdoel"]


class BuurtSerializer(GeoFeatureModelSerializer):
    geom = SridGeometryField()

    class Meta:
        model = Buurt
        geo_field = "geom"
        fields = ["id", "buurtcode", "buurtnaam", "aantalinwoners", "dichtheid"]


class ProjectSerializer(GeoFeatureModelSerializer):
    locatie = SridGeometryField()

    class Meta:
        model = Project
        geo_field = "locatie"
        fields = ["id", "naam", "opdrachtgever", "status"]


class PandFilter(df.FilterSet):
    class Meta:
        model = Pand
        fields = {"bouwjaar": ["exact", "gte", "lte"], "status": ["exact"]}


@extend_schema_view(list=extend_schema(parameters=[SRID_PARAM]))
class PandViewSet(viewsets.ReadOnlyModelViewSet):
    """Panden (BAG) als GeoJSON FeatureCollection, gepagineerd."""

    queryset = Pand.objects.all()
    serializer_class = PandSerializer
    bbox_filter_field = "geom"
    filter_backends = [SridBBoxFilter, df.DjangoFilterBackend]
    filterset_class = PandFilter


@extend_schema_view(list=extend_schema(parameters=[SRID_PARAM]))
class BuurtViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Buurt.objects.all()
    serializer_class = BuurtSerializer
    bbox_filter_field = "geom"
    filter_backends = [SridBBoxFilter]


@extend_schema_view(list=extend_schema(parameters=[SRID_PARAM]))
class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    bbox_filter_field = "locatie"
    filter_backends = [SridBBoxFilter, df.DjangoFilterBackend]
    filterset_fields = ["status"]
