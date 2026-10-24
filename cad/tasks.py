"""Celery-taken voor de CAD-pipeline (les 22).

Keuze: ``pipeline/django-integratie/rcs_tasks.py`` importeert ``aps_da`` (buiten een Django-app,
roept Design Automation aan en vraagt credentials). Voor de lokale run zonder APS staat hier een
eigen taak die ``autocad/python-ezdxf/rcs_check.py --json`` aanroept: dezelfde regels, geen AutoCAD.
"""

import json
import subprocess
import sys
from pathlib import Path

from celery import shared_task
from django.conf import settings

RCS_CHECK = Path(settings.BASE_DIR) / "autocad" / "python-ezdxf" / "rcs_check.py"


@shared_task(
    name="cad.rcs_check",
    autoretry_for=(subprocess.TimeoutExpired,),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=3,
)
def rcs_check(dxf_pad: str) -> dict:
    """Voert rcs_check.py uit op een DXF. Exit 1 (bevindingen) is geen fout; andere exits wel."""
    pad = Path(dxf_pad)
    if not pad.is_absolute():
        pad = Path(settings.BASE_DIR) / pad
    p = subprocess.run(
        [sys.executable, str(RCS_CHECK), str(pad), "--json"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if p.returncode not in (0, 1):
        raise RuntimeError(f"rcs_check exit {p.returncode}: {p.stderr.strip()[:300]}")
    try:
        data = json.loads(p.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"rcs_check exit {p.returncode}: {p.stderr.strip()[-300:]}") from None
    return {
        "bestand": data["bestand"],
        "aantal_bevindingen": data["aantal_bevindingen"],
        "bevindingen": data["bevindingen"],
        "ruimten": len(data["ruimten"]),
    }
