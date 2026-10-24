import json
from math import cos, radians, sin
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from cad import georef
from cad.importeren import importeer_dxf
from cad.management.commands.georefereer import lees_paspunten
from cad.models import Tekening

DATA = Path(__file__).resolve().parents[2] / "data" / "cad"
WAARHEID = DATA / "georef-waarheid.json"


def _punten(n=4, matrix=(0.9, 0.4, 143000.0, -0.4, 0.9, 487000.0)):
    """Exacte paspunten uit een bekende transformatie (lokaal in m)."""
    lokaal = [(0, 0), (30, 0), (30, 30), (0, 30), (10, 20)][:n]
    a, b, c, d, e, f = matrix
    return [
        {"naam": "ABCDE"[i], "lokaal": [x, y], "rd": [a * x + b * y + c, d * x + e * y + f]}
        for i, (x, y) in enumerate(lokaal)
    ]


def test_bekende_transformatie_wordt_teruggerekend():
    matrix = (0.9, 0.4, 143000.0, -0.4, 0.9, 487000.0)
    r = georef.bereken(_punten(5, matrix), "affien")
    assert r.matrix == pytest.approx(matrix, abs=1e-6)
    assert r.rmse < 1e-6


def test_helmert_vindt_rotatie_en_schaal():
    s, hoek = 1.25, -18.998
    a, b = s * cos(radians(hoek)), -s * sin(radians(hoek))
    matrix = (a, b, 143067.5, -b, a, 487778.25)
    r = georef.bereken(_punten(4, matrix), "helmert")
    assert r.matrix == pytest.approx(matrix, abs=1e-6)
    assert r.rotatie_graden == pytest.approx(hoek, abs=1e-6)
    assert r.schaal == pytest.approx(s, abs=1e-9)


def test_drie_punten_geven_restfout_nul_ook_met_fout_punt():
    punten = _punten(3)
    punten[2]["rd"][0] += 5.0  # fout punt, toch rmse 0: geen controle
    r = georef.bereken(punten, "affien")
    assert r.rmse < 1e-6
    assert georef.bereken(punten[:2], "helmert").rmse < 1e-6
    with pytest.raises(ValueError):
        georef.bereken(punten[:2], "affien")


def test_fout_punt_geeft_grootste_residu_op_dat_punt():
    # vijf punten (met een middenpunt): affien kan een punt dan niet meer verbergen
    punten = _punten(5)
    punten[4]["rd"][1] += 2.0
    r = georef.bereken(punten, "affien")
    assert max(range(5), key=lambda i: r.residuen[i]) == 4
    assert r.rmse > 0.1
    # Helmert wijst ook bij de 4 paspunten uit de waarheid de dader aan (gemeten, r19-04)
    vier = _punten(4)
    vier[2]["rd"][0] += 2.0
    h = georef.bereken(vier, "helmert")
    assert max(range(4), key=lambda i: h.residuen[i]) == 2


def test_waarheid_paspunten_en_foutvariant():
    punten = lees_paspunten(WAARHEID)
    r = georef.bereken(punten, "affien")
    assert r.rmse < 0.001
    assert r.rotatie_graden == pytest.approx(-18.998031, abs=0.001)
    assert r.schaal == pytest.approx(1.0, abs=1e-4)
    punten[2]["rd"][0] += 2.0
    assert georef.bereken(punten, "helmert").residuen[2] == max(
        georef.bereken(punten, "helmert").residuen
    )
    assert georef.bereken(punten, "affien").rmse > 0.3


@pytest.mark.django_db
def test_command_vult_geom_rd_binnen_bagpand(tmp_path):
    t = Tekening.objects.create(naam="t.dxf", eenheid="?")
    importeer_dxf(DATA / "plattegrond-bg.dxf", t)
    assert t.ruimtes.filter(geom_rd__isnull=False).count() == 0
    call_command("georefereer", t.pk, paspunten=WAARHEID, stdout=open(tmp_path / "u", "w"))
    pand = json.loads((DATA / "pand.json").read_text())["hoekpunten_rd"]
    xs = [p[0] for p in pand.values()]
    ys = [p[1] for p in pand.values()]
    ruimtes = list(t.ruimtes.all())
    assert len(ruimtes) == 11
    for ruimte in ruimtes:
        assert ruimte.geom_rd.srid == 28992
        x0, y0, x1, y1 = ruimte.geom_rd.extent
        assert min(xs) - 0.05 <= x0 and x1 <= max(xs) + 0.05
        assert min(ys) - 0.05 <= y0 and y1 <= max(ys) + 0.05
    t.refresh_from_db()
    assert t.georef["rmse_m"] < 0.001 and len(t.paspunten) == 4


@pytest.mark.django_db
def test_postgis_st_affine_geeft_hetzelfde_als_python():
    t = Tekening.objects.create(naam="t.dxf", eenheid="?")
    importeer_dxf(DATA / "plattegrond-bg.dxf", t)
    m = (0.9455, 0.3255, 143067.66, -0.3255, 0.9455, 487778.19)
    for ruimte in t.ruimtes.all():
        py = georef.pas_toe(ruimte.geom, m)
        pg = georef.pas_toe_postgis(ruimte.geom, m)
        assert py.srid == pg.srid == 28992
        assert [w for pt in py.coords[0] for w in pt] == pytest.approx(
            [w for pt in pg.coords[0] for w in pt], abs=1e-9
        )


@pytest.mark.django_db
def test_command_weigert_onbekende_tekening(tmp_path):
    with pytest.raises(CommandError):
        call_command("georefereer", 999999, paspunten=WAARHEID)


@pytest.mark.django_db
def test_max_rmse_weigert_fout_set(tmp_path):
    t = Tekening.objects.create(naam="t.dxf", eenheid="?")
    importeer_dxf(DATA / "plattegrond-bg.dxf", t)
    data = json.loads(WAARHEID.read_text())
    punten = data["paspunten"] if isinstance(data, dict) else data
    punt_c = next(p for p in punten if p["naam"] == "C")
    punt_c["rd_m"][0] += 2.0
    fout = tmp_path / "fout.json"
    fout.write_text(json.dumps(data))
    with pytest.raises(CommandError, match="hoger dan de drempel"):
        call_command("georefereer", t.pk, paspunten=fout, max_rmse=0.1)
    assert not t.ruimtes.exclude(geom_rd=None).exists()
    out = tmp_path / "u"
    call_command("georefereer", t.pk, paspunten=WAARHEID, max_rmse=0.1, stdout=open(out, "w"))
    assert t.ruimtes.exclude(geom_rd=None).count() == 11
