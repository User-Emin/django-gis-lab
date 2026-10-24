import pytest
from django.contrib.gis.geos import MultiPolygon, Point, Polygon

from kaart.models import Pand, Project

pytestmark = pytest.mark.django_db

# Twee RD-vierkanten: A ligt binnen de zoekbbox, B steekt er half buiten uit.
BBOX_RD = "143000,486000,143100,486100"


@pytest.fixture
def panden(django_db_setup):
    def maak(gid, x0, jaar):
        p = Polygon(
            ((x0, 486010), (x0, 486030), (x0 + 20, 486030), (x0 + 20, 486010), (x0, 486010))
        )
        return Pand.objects.create(
            gid=gid,
            identificatie=f"{gid:016d}",
            bouwjaar=jaar,
            status="Pand in gebruik",
            aantal_verblijfsobjecten=1,
            geom=MultiPolygon(p, srid=28992),
        )

    return maak(1, 143010, 1985), maak(2, 143090, 2005)


def test_geojson_structuur_en_wgs84_standaard(client, panden):
    d = client.get("/api/panden/").json()
    assert d["type"] == "FeatureCollection" and d["count"] == 2
    lon, lat = d["features"][0]["geometry"]["coordinates"][0][0][0]
    assert 4 < lon < 6 and 51 < lat < 53  # Almere in graden


def test_srid_28992_geeft_meters(client, panden):
    d = client.get("/api/panden/?srid=28992").json()
    x, y = d["features"][0]["geometry"]["coordinates"][0][0][0]
    assert x == 143010 and y == 486010


def test_contained_versus_overlap(client, panden):
    q = f"/api/panden/?srid=28992&in_bbox={BBOX_RD}"
    assert client.get(q).json()["count"] == 1
    assert client.get(q + "&bbox_modus=overlap").json()["count"] == 2


def test_bbox_in_graden_op_rd_veld_zonder_srid_is_leeg(panden):
    # De fout uit de les: Polygon zonder SRID wordt als veld-SRID (28992) gelezen
    bbox = Polygon.from_bbox((5.20, 52.36, 5.23, 52.38))
    assert Pand.objects.filter(geom__contained=bbox).count() == 0


def test_srid_onbekend_is_400(client, panden):
    r = client.get("/api/panden/?srid=3857")
    assert r.status_code == 400 and "niet toegestaan" in r.json()["detail"]


def test_bbox_geen_getallen_is_400(client, panden):
    assert client.get("/api/panden/?in_bbox=a,b,c,d").status_code == 400


def test_filter_bouwjaar_en_paginering(client, panden):
    d = client.get("/api/panden/?bouwjaar__gte=2000&page_size=1").json()
    assert d["count"] == 1 and len(d["features"]) == 1 and d["next"] is None
    d = client.get("/api/panden/?page_size=1").json()
    assert d["count"] == 2 and d["next"]


def test_project_punt_en_schrijven_kan_niet(client, panden):
    Project.objects.create(
        naam="P", opdrachtgever="G", locatie=Point(143515.95, 486811.47, srid=28992)
    )
    d = client.get("/api/projecten/").json()
    lon, lat = d["features"][0]["geometry"]["coordinates"]
    assert round(lon, 3) == 5.219 and round(lat, 3) == 52.369
    assert client.post("/api/projecten/", {"naam": "x"}).status_code == 405


def test_schema_valide(client):
    from django.core.management import call_command

    call_command("spectacular", "--validate", "--fail-on-warn", file="/dev/null")


def ids(antwoord):
    return [f["properties"]["identificatie"].lstrip("0") for f in antwoord["features"]]


def test_afstandsfilter_op_punt(client, panden):
    # Pand 1 (143010..143030, 486010..486030) in WGS84-midden; punt = midden van pand 1.
    for p in panden:
        p.refresh_from_db()
    from django.core.management import call_command

    call_command("vul_midden")
    midden = Pand.objects.get(gid=1).midden_geo
    punt = f"{midden.x},{midden.y}"
    dichtbij = client.get(f"/api/panden/?point={punt}&dist=50").json()
    assert ids(dichtbij) == ["1"]
    ver = client.get(f"/api/panden/?point={punt}&dist=1000&order=asc").json()
    assert ids(ver) == ["1", "2"]
    omgekeerd = client.get(f"/api/panden/?point={punt}&dist=1000&order=desc").json()
    assert ids(omgekeerd) == ["2", "1"]
