"""Tests voor de laagnaam-whitelist van rcs_check (--lagen <bestand>)."""

import importlib.util
import subprocess
import sys
from pathlib import Path

AUTOCAD = Path(__file__).resolve().parents[1]
DATA = AUTOCAD.parent / "data" / "cad"
FOUTEN_DXF = str(DATA / "plattegrond-bg-fouten.dxf")


def _laad(pad):
    spec = importlib.util.spec_from_file_location(pad.stem, pad)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rcs_check = _laad(AUTOCAD / "python-ezdxf" / "rcs_check.py")


def _laagfouten(regels):
    return [r for r in regels if r.startswith("FOUT laagnaam")]


def test_zonder_whitelist_is_ruimten_een_laagnaamfout():
    regels, _ = rcs_check.controleer(FOUTEN_DXF)
    assert any("'Ruimten'" in r for r in _laagfouten(regels))


def test_whitelist_laat_exacte_laagnaam_door(tmp_path):
    bestand = tmp_path / "lagen.txt"
    bestand.write_text("Ruimten\n", encoding="utf-8")
    toegestaan = rcs_check.laad_whitelist(str(bestand))
    regels, _ = rcs_check.controleer(FOUTEN_DXF, toegestaan=toegestaan)
    assert _laagfouten(regels) == []
    assert any(r.startswith("Klaar: 4 bevinding(en)") for r in regels)


def test_whitelist_patroon_en_lege_regels(tmp_path):
    bestand = tmp_path / "lagen.txt"
    bestand.write_text("\nRuim*\n\n", encoding="utf-8")
    assert rcs_check.laad_whitelist(str(bestand)) == ["Ruim*"]


def test_cli_optie_lagen(tmp_path):
    bestand = tmp_path / "lagen.txt"
    bestand.write_text("Ruimten\n", encoding="utf-8")
    p = subprocess.run(
        [
            sys.executable,
            str(AUTOCAD / "python-ezdxf" / "rcs_check.py"),
            FOUTEN_DXF,
            "--lagen",
            str(bestand),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert "FOUT laagnaam" not in p.stdout
    assert "Klaar: 4 bevinding(en)" in p.stdout
