from io import StringIO

import pytest
from django.core.cache import cache
from django.core.management import call_command

from kaart import tiles

pytestmark = pytest.mark.django_db

MVT = "application/vnd.mapbox-vector-tile"


def tegel_voor(z: int, rd_x: float, rd_y: float) -> tuple[int, int]:
    breedte = tiles.tegelbreedte(z)
    return int((rd_x - tiles.GRID[0]) // breedte), int((tiles.GRID[3] - rd_y) // breedte)


@pytest.fixture
def almere(db):
    call_command("laad_almere", stdout=StringIO())
    cache.clear()


def test_tile_over_almere(client, almere):
    x, y = tegel_voor(9, 143515, 486811)
    antwoord = client.get(f"/tiles/panden/9/{x}/{y}.pbf")
    assert antwoord.status_code == 200
    assert antwoord["Content-Type"] == MVT
    assert len(antwoord.content) > 1000
    assert antwoord["X-Tile-Cache"] == "MISS"


def test_tile_buiten_almere_is_leeg(client, almere):
    antwoord = client.get("/tiles/panden/9/10/10.pbf")
    assert antwoord.status_code == 200
    assert antwoord["Content-Type"] == MVT
    assert antwoord.content == b""


def test_cache_header_en_tweede_keer_uit_cache(client, almere):
    x, y = tegel_voor(10, 143515, 486811)
    url = f"/tiles/panden/10/{x}/{y}.pbf"
    eerste = client.get(url)
    tweede = client.get(url)
    assert "max-age=3600" in eerste["Cache-Control"]
    assert "public" in eerste["Cache-Control"]
    assert eerste["X-Tile-Cache"] == "MISS"
    assert tweede["X-Tile-Cache"] == "HIT"
    assert tweede.content == eerste.content


def test_vereenvoudigen_maakt_tile_kleiner(client, almere):
    x, y = tegel_voor(7, 143515, 486811)
    url = f"/tiles/panden/7/{x}/{y}.pbf"
    klein = client.get(url)
    cache.clear()
    groot = client.get(url + "?vereenvoudig=geen")
    assert 0 < len(klein.content) < len(groot.content)


def test_zoom_of_positie_buiten_grid_is_404(client, almere):
    assert client.get("/tiles/panden/15/0/0.pbf").status_code == 404
    assert client.get("/tiles/panden/3/8/0.pbf").status_code == 404


def test_alleen_get(client, almere):
    assert client.post("/tiles/panden/9/10/10.pbf").status_code == 405
