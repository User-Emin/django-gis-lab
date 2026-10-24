from unittest import mock

import pytest
from django.db import OperationalError


@pytest.mark.django_db
def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok"}


def test_health_db_weg(client):
    with mock.patch("kaart.health.connection") as verbinding:
        verbinding.cursor.side_effect = OperationalError("weg")
        response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["status"] == "fout"


@pytest.mark.django_db
def test_ready_ok(client):
    with mock.patch("kaart.health._redis_ok", return_value=True):
        response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok", "redis": "ok"}


@pytest.mark.django_db
def test_ready_redis_weg(client):
    with mock.patch("kaart.health._redis_ok", return_value=False):
        response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "fout", "db": "ok", "redis": "onbereikbaar"}


def test_ready_db_weg(client):
    with (
        mock.patch("kaart.health._db_ok", return_value=False),
        mock.patch("kaart.health._redis_ok", return_value=True),
    ):
        response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["db"] == "onbereikbaar"


def test_redis_ok_zonder_server(settings):
    from kaart.health import _redis_ok

    settings.CELERY_BROKER_URL = "redis://127.0.0.1:1/0"  # niets luistert hier
    assert _redis_ok() is False
