import json
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import MultiPolygon, Polygon
from django.core.management import call_command

from cad import kwaliteit
from cad.importeren import importeer_dxf
from cad.models import Tekening
from kaart.models import Pand

DATA = Path(__file__).resolve().parents[2] / "data" / "cad"
WAARHEID = DATA / "georef-waarheid.json"

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.skipif(not WAARHEID.exists(), reason="georef-waarheid ontbreekt"),
]


def _tekening(dxf: str, georefereer: bool = True) -> Tekening:
    t = Tekening.objects.create(naam=dxf, eenheid="?")
    importeer_dxf(DATA / dxf, t)
    if georefereer:
        call_command("georefereer", t.pk, paspunten=WAARHEID, stdout=open("/dev/null", "w"))
    return t


@pytest.fixture
def pand(db):
    punten = json.loads((DATA / "pand.json").read_text())["hoekpunten_rd"]
    ring = [tuple(p) for p in punten.values()]
    return Pand.objects.create(
        gid=990001,
        identificatie=kwaliteit.STANDAARD_PAND,
        bouwjaar=2002,
        status="Pand in gebruik",
        aantal_verblijfsobjecten=3,
        geom=MultiPolygon(Polygon([*ring, ring[0]], srid=28992), srid=28992),
    )


@pytest.fixture
def goed(db, pand):
    return _tekening("plattegrond-bg.dxf")


@pytest.fixture
def fouten(db, pand):
    return _tekening("plattegrond-bg-fouten.dxf")


@pytest.fixture
def client(client, db):
    gebruiker = get_user_model().objects.create_user("tester", password="x")
    client.force_login(gebruiker)
    return client


def test_goede_tekening_is_schoon(goed):
    assert all(r["geldig"] for r in kwaliteit.geldigheid(goed.pk))
    assert kwaliteit.overlap(goed.pk) == []
    assert kwaliteit.pandverschil(goed.pk)["buiten_m2"] == pytest.approx(0, abs=0.01)


def test_fouten_00_06_is_ongeldig_en_makevalid_geeft_multipolygon(fouten):
    rij = next(r for r in kwaliteit.geldigheid(fouten.pk) if r["nummer"] == "00.06")
    assert rij["geldig"] is False
    assert "Self-intersection" in rij["reden"]
    assert rij["oppervlakte_voor"] < 0.1
    assert rij["type_na"] == "MULTIPOLYGON"
    assert rij["oppervlakte_na"] == pytest.approx(26.94, abs=0.05)


def test_overlap_00_02_00_03(fouten):
    paren = kwaliteit.overlap(fouten.pk)
    assert [(p["a"], p["b"]) for p in paren] == [("00.02", "00.03")]
    assert paren[0]["oppervlakte"] == pytest.approx(11.60, abs=0.05)


def test_api_crs_rd_409_zonder_geom_rd(client, pand):
    t = _tekening("plattegrond-bg.dxf", georefereer=False)
    r = client.get(f"/cad/api/tekening/{t.pk}/ruimtes/?crs=rd")
    assert r.status_code == 409
    assert client.get(f"/cad/api/tekening/{t.pk}/ruimtes/").status_code == 200


def test_api_crs_rd_geeft_rd_coordinaten(client, goed):
    r = client.get(f"/cad/api/tekening/{goed.pk}/ruimtes/?crs=rd")
    assert r.status_code == 200
    data = r.json()
    assert data["crs"] == "EPSG:28992"
    assert len(data["features"]) == 11
    for f in data["features"]:
        for x, y in f["geometry"]["coordinates"][0]:
            assert 0 < x < 300000
            assert 300000 < y < 620000


def test_api_fouten(client, fouten, goed):
    data = client.get(f"/cad/api/tekening/{fouten.pk}/fouten/").json()
    soorten = [f["properties"]["soort"] for f in data["features"]]
    assert sorted(soorten) == ["overlap", "pand"]
    overlap = next(f for f in data["features"] if f["properties"]["soort"] == "overlap")
    assert overlap["properties"]["tussen"] == "00.02 / 00.03"
    assert overlap["properties"]["m2"] == pytest.approx(11.60, abs=0.05)
    assert data["samenvatting"]["ongeldig"] == ["00.06"]
    schoon = client.get(f"/cad/api/tekening/{goed.pk}/fouten/").json()
    assert [f["properties"]["soort"] for f in schoon["features"]] == ["pand"]
    assert schoon["samenvatting"]["overlap"] == []
