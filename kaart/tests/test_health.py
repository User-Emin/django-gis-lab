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
