"""Les 20: export GIS -> DXF, met dezelfde aanpak als test_kwaliteit (echte import + georef)."""

import json
from pathlib import Path

import ezdxf
import pytest
from django.contrib.gis.geos import MultiPolygon, Polygon
from django.db import connection

from cad import exporteren, kwaliteit
from cad.dxf import RUIMTELAAG
from cad.tests.test_kwaliteit import DATA, WAARHEID
from cad.tests.test_kwaliteit import _tekening as _tekening_stale
from kaart.models import Pand

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.skipif(not WAARHEID.exists(), reason="georef-waarheid ontbreekt"),
]


def _tekening(dxf: str, georefereer: bool = True):
    """De georefereer-command schrijft in de database; ververs het object met georef."""
    t = _tekening_stale(dxf, georefereer)
    t.refresh_from_db()
    return t


VERWACHTE_LAGEN = {RUIMTELAAG, "00 BAG-pand", "99 Tekst"}


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


def _opslaan_en_lezen(tekening, crs, tmp_path: Path):
    """Schrijf naar schijf en lees terug: we testen het bestand, niet het geheugenobject."""
    doc, rapport = exporteren.exporteer(tekening, crs)
    pad = tmp_path / f"{crs}.dxf"
    doc.saveas(pad)
    return ezdxf.readfile(pad), rapport


def _oppervlakte(punten) -> float:
    """Shoelace; punten is een gesloten polylijn zonder herhaald eindpunt.

    Eerst naar het eerste punt verschoven: met RD-coordinaten (1e5) geeft de kruisproductsom
    anders afrondfouten van ~1e-5 m2.
    """
    x0, y0 = punten[0][0], punten[0][1]
    punten = [(p[0] - x0, p[1] - y0) for p in punten]
    n = len(punten)
    s = sum(
        punten[i][0] * punten[(i + 1) % n][1] - punten[(i + 1) % n][0] * punten[i][1]
        for i in range(n)
    )
    return abs(s) / 2


def _polylijnen(doc, laag):
    return list(doc.modelspace().query(f'LWPOLYLINE[layer=="{laag}"]'))


def test_lagen_zijn_er_en_laag_0_is_leeg(goed, tmp_path):
    doc, _ = _opslaan_en_lezen(goed, "rd", tmp_path)
    lagen = {layer.dxf.name for layer in doc.layers}
    assert VERWACHTE_LAGEN <= lagen
    assert "00 Controle" not in lagen  # geen fouten: geen lege laag (RCS)
    gebruikt = {e.dxf.layer for e in doc.modelspace()}
    assert "0" not in gebruikt
    assert gebruikt <= lagen


def test_laag_92_heeft_11_gesloten_polylines(goed, tmp_path):
    doc, rapport = _opslaan_en_lezen(goed, "rd", tmp_path)
    pls = _polylijnen(doc, RUIMTELAAG)
    assert len(pls) == 11 == rapport["ruimtes"]
    assert all(pl.closed for pl in pls)


@pytest.mark.parametrize("crs,code", [("rd", 6), ("lokaal", 4)])
def test_insunits_per_crs(goed, tmp_path, crs, code):
    doc, rapport = _opslaan_en_lezen(goed, crs, tmp_path)
    assert doc.header["$INSUNITS"] == code == rapport["insunits"]


def test_rondreis_lokaal_via_geom_rd_is_klein_en_niet_triviaal(goed, tmp_path):
    doc_lok, _ = _opslaan_en_lezen(goed, "lokaal", tmp_path)
    doc_rd, _ = _opslaan_en_lezen(goed, "rd", tmp_path)

    # Niet triviaal: de RD-punten zijn echt anders dan de lokale (m versus mm, ander stelsel).
    rd0 = _polylijnen(doc_rd, RUIMTELAAG)[0].get_points("xy")[0]
    lok0 = _polylijnen(doc_lok, RUIMTELAAG)[0].get_points("xy")[0]
    assert rd0[0] > 100_000 and rd0[1] > 300_000  # RD-bereik
    assert abs(lok0[0]) < 100_000 and abs(lok0[1]) < 100_000  # lokale mm
    assert abs(rd0[0] - lok0[0]) > 1000

    # De keten loopt via geom_rd en de inverse matrix, niet via Ruimte.geom.
    r = exporteren.rondreis(goed, doc_lok, "lokaal")
    assert r["n"] == 11
    assert r["max_afwijking_vs_db"] < 1e-3  # mm

    # Gevoeligheid: schuif geom_rd 1 mm (0,001 m) op en exporteer opnieuw; de meting tegenover
    # Ruimte.geom moet dat zien (~0,95 mm, zoals gemeten in r20-02).
    for ruimte in goed.ruimtes.all():
        ring = [(x + 0.001, y) for x, y in ruimte.geom_rd.coords[0]]
        ruimte.geom_rd = Polygon(ring, srid=28992)
        ruimte.save(update_fields=["geom_rd"])
    doc_gestoord, _ = _opslaan_en_lezen(goed, "lokaal", tmp_path)
    gestoord = exporteren.rondreis(goed, doc_gestoord, "lokaal")
    assert 0.5 < gestoord["max_afwijking_vs_db"] < 1.5  # mm


def test_oppervlaktesom_export_gelijk_aan_db(goed, tmp_path):
    with connection.cursor() as cur:
        cur.execute(
            "SELECT sum(ST_Area(geom_rd)) FROM cad_ruimte WHERE tekening_id = %s", [goed.pk]
        )
        db_m2 = cur.fetchone()[0]
        cur.execute("SELECT sum(ST_Area(geom)) FROM cad_ruimte WHERE tekening_id = %s", [goed.pk])
        db_lokaal_m2 = cur.fetchone()[0]
    rd, _ = _opslaan_en_lezen(goed, "rd", tmp_path)
    lok, _ = _opslaan_en_lezen(goed, "lokaal", tmp_path)
    som_rd = sum(_oppervlakte(pl.get_points("xy")) for pl in _polylijnen(rd, RUIMTELAAG))
    som_lok = sum(_oppervlakte(pl.get_points("xy")) for pl in _polylijnen(lok, RUIMTELAAG))
    assert db_m2 == pytest.approx(813.914, abs=0.001)
    assert som_rd == pytest.approx(db_m2, abs=1e-6)
    # lokaal is een ander stelsel (affiene schaal niet exact 1): vergelijk met geom, niet geom_rd
    assert som_lok / 1e6 == pytest.approx(db_lokaal_m2, abs=1e-6)  # mm2 -> m2


def test_fouten_export_heeft_laag_00_controle(fouten, tmp_path):
    doc, rapport = _opslaan_en_lezen(fouten, "rd", tmp_path)
    assert rapport["fouten"]["ongeldig"] == ["00.06"]
    assert [o[:2] for o in rapport["fouten"]["overlap"]] == [["00.02", "00.03"]]
    laag = doc.layers.get("00 Controle")
    assert laag.dxf.color == 1  # rood
    soorten = sorted(e.dxftype() for e in doc.modelspace() if e.dxf.layer == "00 Controle")
    assert soorten == ["LWPOLYLINE", "LWPOLYLINE", "TEXT", "TEXT"]


def test_zonder_controle_laat_controlelaag_weg(fouten, tmp_path):
    doc, rapport = exporteren.exporteer(fouten, "rd", controle=False)
    pad = tmp_path / "zc.dxf"
    doc.saveas(pad)
    doc = ezdxf.readfile(pad)
    assert "00 Controle" not in {laag.dxf.name for laag in doc.layers}
    assert len(_polylijnen(doc, "92 Rust- en werkgebieden")) == 9
    assert rapport["fouten"]["ongeldig"] == ["00.06"]  # de fouten worden wel gemeld


def test_export_zonder_georef_geeft_fout(db, pand):
    t = _tekening("plattegrond-bg.dxf", georefereer=False)
    with pytest.raises(exporteren.ExportFout):
        exporteren.exporteer(t, "rd")
