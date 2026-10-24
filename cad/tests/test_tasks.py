from pathlib import Path
from unittest.mock import patch

import pytest
from django.conf import settings
from django.test import Client

from cad.tasks import rcs_check

DATA = Path(settings.BASE_DIR) / "data" / "cad"


@pytest.fixture(autouse=True)
def eager(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_STORE_EAGER_RESULT = False
    from projectkaart import celery_app

    celery_app.conf.task_always_eager = True


def test_goede_dxf_geen_bevindingen():
    r = rcs_check.delay(str(DATA / "plattegrond-bg.dxf"))
    assert r.status == "SUCCESS"
    assert r.result["aantal_bevindingen"] == 0


def test_fouten_dxf_vijf_bevindingen_met_overlap():
    r = rcs_check.delay(str(DATA / "plattegrond-bg-fouten.dxf"))
    assert r.result["aantal_bevindingen"] == 5
    assert any("11.60 m2" in b for b in r.result["bevindingen"])


def test_ontbrekend_bestand_faalt():
    with pytest.raises(RuntimeError):
        rcs_check.apply(args=["bestaat-niet.dxf"], throw=True)


def test_statuspagina_json():
    c = Client()
    with (
        patch("celery.result.AsyncResult.status", "PENDING"),
        patch("celery.result.AsyncResult.successful", return_value=False),
        patch("celery.result.AsyncResult.failed", return_value=False),
    ):
        r = c.get("/cad/taak/onbekend-id/?format=json")
    assert r.status_code == 200
    assert r.json()["status"] == "PENDING"


def test_timeout_wordt_herhaald_met_max_retries():
    import subprocess

    from celery.exceptions import Retry  # noqa: F401

    assert rcs_check.max_retries == 3
    assert rcs_check.retry_backoff is True
    with patch("cad.tasks.subprocess.run", side_effect=subprocess.TimeoutExpired("x", 1)) as run:
        r = rcs_check.apply(args=[str(DATA / "plattegrond-bg.dxf")])
    assert r.status == "FAILURE"
    assert run.call_count == 4  # 1 poging + 3 herhalingen
