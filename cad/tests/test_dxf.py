import re
from io import StringIO
from pathlib import Path

import ezdxf
import pytest
from django.core.management import call_command

from cad import dxf

DATA = Path(__file__).resolve().parents[2] / "data" / "cad"

# Laagnamen volgens bron/rcs-lagen.md (sectie C); Defpoints maakt ezdxf/AutoCAD zelf.
VERWACHTE_LAGEN = {
    "0",
    "Defpoints",
    "21 Buitenwanden",
    "22 Binnenwanden",
    "31 Buitenwandopeningen",
    "32 Binnenwandopeningen",
    "92 Rust- en werkgebieden",
    "99 Maatvoering",
    "99 Tekst",
}
RCS_LAAGSYNTAX = re.compile(r"^\d{2} [\w\- ]+$")


@pytest.fixture(scope="module")
def doc():
    return ezdxf.readfile(DATA / "plattegrond-bg.dxf")


def test_lagen_kloppen_met_rcs_lagen(doc):
    namen = {laag["naam"] for laag in dxf.lagen(doc)}
    assert namen == VERWACHTE_LAGEN
    for naam in namen - {"0", "Defpoints"}:
        assert RCS_LAAGSYNTAX.match(naam), naam


def test_geen_lege_lagen_behalve_0_en_defpoints(doc):
    gebruikt = {laag for _, laag in dxf.tel_entiteiten(doc.modelspace())}
    assert VERWACHTE_LAGEN - {"Defpoints"} == gebruikt


def test_elf_ruimtes(doc):
    r = dxf.ruimtes(doc)
    assert len(r) == 11
    assert [x.nummer for x in r] == [f"00.{i:02d}" for i in range(1, 12)]
    assert all(x.oppervlak_m2 > 10 for x in r)


def test_ruimtes_in_fouten_dxf_slaat_open_contour_en_verkeerde_laag_over():
    fout = ezdxf.readfile(DATA / "plattegrond-bg-fouten.dxf")
    assert len(dxf.ruimtes(fout)) == 9


def test_bulge_naar_boog_geeft_straal_van_de_deurboog(doc):
    # De deurboog in de generator is een kwartcirkel (bulge tan(22,5 graden)) met de
    # deurbreedte DW = 900 mm als straal.
    pl = next(
        e for e in doc.modelspace().query("LWPOLYLINE") if any(p[2] for p in dxf.polylijn_punten(e))
    )
    (x1, y1, b), (x2, y2, _) = dxf.polylijn_punten(pl)[:2]
    boog = dxf.bulge_naar_boog((x1, y1), (x2, y2), b)
    assert boog["straal"] == pytest.approx(900.0, abs=0.5)
    assert abs(boog["eind_graden"] - boog["start_graden"]) == pytest.approx(90.0, abs=0.1)


def test_bulge_nul_is_geen_boog_en_een_halve_cirkel_heeft_straal_halve_koorde():
    boog = dxf.bulge_naar_boog((0, 0), (10, 0), 1.0)
    assert boog["straal"] == pytest.approx(5.0)
    with pytest.raises(ZeroDivisionError):
        dxf.bulge_naar_boog((0, 0), (10, 0), 0.0)


def test_insunits_is_mm(doc):
    assert doc.header["$INSUNITS"] == 4
    assert dxf.eenheid_naam(doc) == "mm"
    assert dxf.meter_per_unit(doc) == pytest.approx(0.001)


def test_oppervlakte_in_m2_en_niet_in_mm2(doc):
    ruimte = dxf.ruimtes(doc)[0]
    assert 10 < ruimte.oppervlak_m2 < 200  # m2, niet 10**6 keer groter


def test_dxf_inhoud_draait(capsys):
    out = StringIO()
    call_command("dxf_inhoud", DATA / "plattegrond-bg.dxf", stdout=out)
    tekst = out.getvalue()
    for kopje in ("== HEADER", "== TABLES", "== BLOCKS", "== ENTITIES", "RUIMTELABEL"):
        assert kopje in tekst
    assert "$INSUNITS     4" in tekst
    assert "101  totaal" in tekst


def test_dxf_inhoud_geeft_nette_fout_bij_ontbrekend_bestand():
    from django.core.management.base import CommandError

    with pytest.raises(CommandError):
        call_command("dxf_inhoud", DATA / "bestaat-niet.dxf")
