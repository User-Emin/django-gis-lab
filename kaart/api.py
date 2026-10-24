import json

from django.contrib.gis.geos import GEOSGeometry, Polygon
from django_filters import rest_framework as df
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ParseError
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework_gis.fields import GeometryField
from rest_framework_gis.filters import (
    DistanceToPointFilter,
    DistanceToPointOrderingFilter,
    InBBoxFilter,
)
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from .models import Buurt, Pand, Project


class SchemaOrderingFilter(DistanceToPointOrderingFilter):
    """drf-gis 1.x zet in het schema `"type": "enum"`, wat geen geldig OpenAPI-type is."""

    def get_schema_operation_parameters(self, view):
        params = super().get_schema_operation_parameters(view)
        params[-1]["schema"] = {"type": "string", "enum": ["asc", "desc"], "example": "asc"}
        return params


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
    # Zelf les 13: ?point=lon,lat&dist=250 (meters, want midden_geo is geography) en &order=asc|desc
    distance_filter_field = "midden_geo"
    distance_filter_convert_meters = (
        False  # True zou meters naar graden omrekenen: fout op geography
    )
    distance_ordering_filter_field = "midden_geo"
    filter_backends = [
        SridBBoxFilter,
        df.DjangoFilterBackend,
        DistanceToPointFilter,
        SchemaOrderingFilter,
    ]
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


# Les 15: schrijven. Alleen dit endpoint vraagt inloggen; de rest blijft AllowAny/alleen lezen.
RD_GRENZEN = (-7000, 289000, 300000, 629000)  # geldigheidsgebied RD New (EPSG:28992), meters


class GebiedSerializer(GeoFeatureModelSerializer):
    gebied = SridGeometryField()

    class Meta:
        model = Project
        geo_field = "gebied"
        fields = ["id", "naam"]


class GebiedInvoer(serializers.Serializer):
    """Body van POST /api/gebieden/: {"project": <id>, "geometry": <GeoJSON Polygon in RD>}."""

    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())
    geometry = serializers.JSONField()

    def validate_geometry(self, waarde):
        try:
            geom = GEOSGeometry(json.dumps(waarde))
            geom.srid = 28992  # GeoJSON-parsing zet 4326; deze API spreekt RD (zoals ?srid=28992)
        except Exception:
            raise serializers.ValidationError("Geen geldige GeoJSON-geometrie.") from None
        if not isinstance(geom, Polygon):
            raise serializers.ValidationError("Alleen een Polygon, geen " + geom.geom_type + ".")
        if not geom.valid:
            raise serializers.ValidationError(f"Ongeldig vlak: {geom.valid_reason}")
        minx, miny, maxx, maxy = geom.extent
        if not (RD_GRENZEN[0] <= minx and maxx <= RD_GRENZEN[2]):
            raise serializers.ValidationError("x buiten het RD-gebied (-7000 tot 300000 m).")
        if not (RD_GRENZEN[1] <= miny and maxy <= RD_GRENZEN[3]):
            raise serializers.ValidationError("y buiten het RD-gebied (289000 tot 629000 m).")
        return geom


@extend_schema_view(list=extend_schema(parameters=[SRID_PARAM]))
class GebiedViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """GET: projecten met een getekend gebied (GeoJSON). POST: gebied van een project opslaan.

    Schrijven vereist een sessie (SessionAuthentication) én het CSRF-token in X-CSRFToken.
    """

    queryset = Project.objects.filter(gebied__isnull=False)
    serializer_class = GebiedSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]
    bbox_filter_field = "gebied"
    filter_backends = [SridBBoxFilter]

    @extend_schema(request=GebiedInvoer, responses={201: GebiedSerializer})
    def create(self, request):
        invoer = GebiedInvoer(data=request.data)
        invoer.is_valid(raise_exception=True)
        project = invoer.validated_data["project"]
        project.gebied = invoer.validated_data["geometry"]
        project.save(update_fields=["gebied"])
        return Response(
            GebiedSerializer(project, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )
