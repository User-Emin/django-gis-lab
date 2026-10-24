from math import pi
from pathlib import Path

import ezdxf
import pytest
from django.core.management import call_command

from cad import dxf
from cad.importeren import ImportFout, importeer_dxf
from cad.models import LOKAAL_SRID, Ruimte, Tekening

DATA = Path(__file__).resolve().parents[2] / "data" / "cad"
LAAG = "92 Rust- en werkgebieden"

pytestmark = pytest.mark.django_db


def _tekening():
    return Tekening.objects.create(naam="t.dxf", eenheid="?")


def _synthetisch(pad, *, insunits=4, vormen=()):
    """Kleine mm-DXF; ``vormen`` zijn (punten, close, tekst) op de ruimtelaag."""
    doc = ezdxf.new("R2018")
    if insunits is None:
        del doc.header["$INSUNITS"]
    else:
        doc.header["$INSUNITS"] = insunits
    doc.layers.add(LAAG)
    msp = doc.modelspace()
    for punten, close, tekst in vormen:
        msp.add_lwpolyline(punten, format="xyb", close=close, dxfattribs={"layer": LAAG})
        if tekst:
            x, y = punten[0][0] + 300, punten[0][1] + 300
            msp.add_text(tekst, dxfattribs={"layer": LAAG, "insert": (x, y)})
    doc.saveas(pad)
    return pad


def test_goed_elf_ruimtes_met_nummers_en_totaal_van_les_17():
    t = _tekening()
    r = importeer_dxf(DATA / "plattegrond-bg.dxf", t)
    ruimtes = Ruimte.objects.filter(tekening=t)
    assert r["aantal_ruimtes"] == ruimtes.count() == 11
    assert sorted(x.nummer for x in ruimtes) == [f"00.{i:02d}" for i in range(1, 12)]
    assert all(x.naam for x in ruimtes)
    les17 = sum(x.oppervlak_m2 for x in dxf.ruimtes(ezdxf.readfile(DATA / "plattegrond-bg.dxf")))
    assert r["totaal_m2"] == pytest.approx(les17, abs=0.01)
    assert not any(x.geometrie_ongeldig for x in ruimtes)
    assert all(x.geom.srid == LOKAAL_SRID == 990001 for x in ruimtes)
    t.refresh_from_db()
    assert t.eenheid == "mm"
    assert t.bag_pand_id == "0034100000049762"
    assert (r["gesloten_gemeld"], r["overgeslagen"], r["genegeerd"]) == ([], [], [])
    assert {i["block"] for i in r["inserts"]} == {"RUIMTELABEL"} and len(r["inserts"]) == 11


def test_fouten_rapport():
    t = _tekening()
    r = importeer_dxf(DATA / "plattegrond-bg-fouten.dxf", t)
    assert r["aantal_ruimtes"] == 9
    assert [x["laag"] for x in r["genegeerd"]] == ["Ruimten"]
    assert len(r["overgeslagen"]) == 1 and r["overgeslagen"][0]["gat_m"] > 8
    assert r["ongeldig"] == ["00.06"]
    assert r["zonder_nummer"] == ["Pantry"]
    nummers = {x["nummer"] for x in r["ruimtes"]}
    assert "00.04" not in nummers and "00.10" not in nummers
    assert Ruimte.objects.get(tekening=t, nummer="00.06").geometrie_ongeldig
    assert Ruimte.objects.filter(tekening=t, geometrie_ongeldig=True).count() == 1


def test_insunits_ontbreekt_weigert_en_slaat_niets_op(tmp_path):
    pad = _synthetisch(
        tmp_path / "a.dxf",
        insunits=None,
        vormen=[([(0, 0), (1000, 0), (1000, 1000), (0, 1000)], True, "01.01")],
    )
    t = _tekening()
    with pytest.raises(ImportFout, match="INSUNITS"):
        importeer_dxf(pad, t)
    assert not Ruimte.objects.exists()


def test_insunits_nul_weigert(tmp_path):
    pad = _synthetisch(tmp_path / "b.dxf", insunits=0)
    with pytest.raises(ImportFout):
        importeer_dxf(pad, _tekening())


def test_bulge_afvlakking_binnen_tolerantie(tmp_path):
    # Vierkant 1 m met een halve cirkel (bulge 1, straal 0,5 m) op de bovenrand.
    # De bulge staat op het beginpunt van het segment (1000,1000) -> (0,1000).
    vorm = [(0, 0, 0), (1000, 0, 0), (1000, 1000, 1), (0, 1000, 0)]
    pad = _synthetisch(tmp_path / "c.dxf", vormen=[(vorm, True, "01.01")])
    exact = 1.0 + pi * 0.5**2 / 2
    t = _tekening()
    r = importeer_dxf(pad, t, boog_tolerantie_m=0.001)
    b = r["ruimtes"][0]["bulge"]
    assert b["exact_m2"] == pytest.approx(exact, abs=1e-6)
    verschil = b["verschil_m2"]
    assert verschil < 0  # ingeschreven lijnstukken: iets kleiner
    assert abs(verschil) <= 0.001 * pi * 0.5  # sagitta-tolerantie x booglengte
    assert Ruimte.objects.get(tekening=t).oppervlakte_m2 == pytest.approx(exact, abs=0.002)
    # grovere tolerantie -> grotere afwijking
    t2 = _tekening()
    grof = importeer_dxf(pad, t2, boog_tolerantie_m=0.05)["ruimtes"][0]["bulge"]["verschil_m2"]
    assert abs(grof) > abs(verschil)


def test_open_polylijn_binnen_tolerantie_wordt_gesloten_en_gemeld(tmp_path):
    klein = [(0, 0, 0), (1000, 0, 0), (1000, 1000, 0), (0, 1000, 0)]
    # 'open' met gat van 20 mm (laatste punt niet op eerste)
    open_klein = [(0, 0, 0), (1000, 0, 0), (1000, 1000, 0), (0, 20, 0)]
    open_groot = [(3000, 0, 0), (4000, 0, 0), (4000, 1000, 0), (3000, 400, 0)]
    pad = _synthetisch(
        tmp_path / "d.dxf",
        vormen=[(klein, True, "01.01"), (open_klein, False, "01.02"), (open_groot, False, "01.03")],
    )
    r = importeer_dxf(pad, _tekening(), sluit_tolerantie_m=0.05)
    assert len(r["gesloten_gemeld"]) == 1 and r["gesloten_gemeld"][0]["gat_m"] == 0.02
    assert len(r["overgeslagen"]) == 1 and r["overgeslagen"][0]["gat_m"] == pytest.approx(0.4)


def test_mtext_geeft_nummer_via_punt_in_polygoon(tmp_path):
    pad = _synthetisch(tmp_path / "e.dxf")
    doc = ezdxf.readfile(pad)
    doc.modelspace().add_lwpolyline(
        [(0, 0), (4000, 0), (4000, 3000), (0, 3000)], close=True, dxfattribs={"layer": LAAG}
    )
    doc.modelspace().add_mtext("01.07\\PKeuken", dxfattribs={"layer": LAAG, "insert": (500, 500)})
    doc.saveas(pad)
    r = importeer_dxf(pad, _tekening())
    assert r["ruimtes"][0]["nummer"] == "01.07"
    assert r["ruimtes"][0]["oppervlakte_m2"] == pytest.approx(12.0)


def test_management_command_print_rapport(capsys, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    call_command("importeer_dxf", DATA / "plattegrond-bg.dxf")
    uit = capsys.readouterr().out
    assert '"aantal_ruimtes": 11' in uit
    assert "0034100000049762" in uit
