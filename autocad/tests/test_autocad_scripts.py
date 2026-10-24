"""Tests voor de Python-kant van les 21 (autocad/): rcs_check, COM-guard, haakjes_check.

LISP, .scr, .NET en het COM-deel zelf draaien niet in deze omgeving (geen AutoCAD/Windows);
daar testen we alleen wat hier echt kan: de ezdxf-referentie, de guard en de haakjescontrole.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

AUTOCAD = Path(__file__).resolve().parents[1]
DATA = AUTOCAD.parent / "data" / "cad"


def _laad(pad):
    spec = importlib.util.spec_from_file_location(pad.stem, pad)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rcs_check = _laad(AUTOCAD / "python-ezdxf" / "rcs_check.py")
haakjes_check = _laad(AUTOCAD / "tools" / "haakjes_check.py")


def _fouten(regels):
    return [r for r in regels if r.startswith("FOUT")]


def test_fouten_dxf_vindt_alle_5_fouten_en_overlap():
    regels, _ = rcs_check.controleer(str(DATA / "plattegrond-bg-fouten.dxf"))
    fouten = _fouten(regels)
    assert len(fouten) == 5
    assert any("niet gesloten" in r and "00.04" in r for r in fouten)
    assert any("FOUT laagnaam" in r for r in fouten)
    assert any("0 ruimtenummers" in r for r in fouten)
    assert any("ongeldige geometrie 00.06" in r for r in fouten)
    assert any("overlap 00.02" in r and "00.03" in r and "11.60 m2" in r for r in fouten)
    assert any(r.startswith("Klaar: 5 bevinding(en)") for r in regels)


def test_goede_dxf_geeft_geen_fouten():
    regels, rijen = rcs_check.controleer(str(DATA / "plattegrond-bg.dxf"))
    assert _fouten(regels) == []
    assert any(r.startswith("Klaar: 0 bevinding(en), 11 ruimtecontour(en)") for r in regels)
    assert len(rijen) == 11


def test_bulge_demo_24_tegenover_26_80():
    regels, rijen = rcs_check.controleer(str(AUTOCAD / "testdata" / "bulge-demo.dxf"))
    assert _fouten(regels) == []
    assert len(rijen) == 1
    assert rijen[0][0] == "00.99"
    assert rijen[0][-2:] == ["24.00", "26.80"]


def test_com_guard_stopt_op_niet_windows():
    if sys.platform == "win32":
        pytest.skip("op Windows probeert het script echt AutoCAD te starten")
    r = subprocess.run(
        [sys.executable, "-I", str(AUTOCAD / "python-com" / "rcs_check_com.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 2
    assert "alleen op Windows" in r.stdout


def test_haakjes_ok_op_echt_lisp_bestand():
    uit = haakjes_check.check((AUTOCAD / "lisp" / "rcs-check.lsp").read_text(encoding="utf-8"))
    assert uit.startswith("OK")


@pytest.mark.parametrize(
    "tekst, deel",
    [
        ("(defun c:a ()\n  (princ (+ 1 2))\n", "niet gesloten"),
        ('(princ "open string)\n', "string niet gesloten"),
    ],
)
def test_haakjes_kapot_bestand_is_geen_ok(tekst, deel):
    uit = haakjes_check.check(tekst)
    assert not uit.startswith("OK")
    assert deel in uit


def test_haakjes_cli_exitcode(tmp_path):
    kapot = tmp_path / "kapot.lsp"
    kapot.write_text("(defun c:a ()\n", encoding="utf-8")
    script = str(AUTOCAD / "tools" / "haakjes_check.py")
    r = subprocess.run(
        [sys.executable, "-I", script, str(kapot)], capture_output=True, text=True, check=False
    )
    assert r.returncode == 1
    assert r.stdout.startswith("kapot.lsp: FOUT")
