"""Les 16: vector tiles (MVT) van de BAG-panden, rechtstreeks uit PostGIS.

Tegelschema (bewuste keuze, zie gemeten.md): RD-tegels op het PDOK-grid van les 14
(origin -285401.92 903401.92, resolutie niveau 0 = 3440.64 m/px, 256 px per tegel).
Dat kan met ST_TileEnvelope zelf, via de vierde parameter `bounds` (PostGIS >= 3.1):
de 'wereld' is dan het vierkant van het PDOK-grid in EPSG:28992 in plaats van Web Mercator.
"""

from django.core.cache import cache
from django.db import connection
from django.http import Http404, HttpResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

# Het vierkant van de PDOK-tilematrix (RD): minx, miny, maxx, maxy
GRID = (-285401.92, 22598.08, 595401.92, 903401.92)
MAX_ZOOM = 14
EXTENT = 4096  # tegel-eenheden per zijde
BUFFER = 64  # eenheden extra rand, zodat lijnen niet aan de tegelrand ophouden
LAAG = "panden"
CONTENT_TYPE = "application/vnd.mapbox-vector-tile"
CACHE_SECONDEN = 3600

# Alles via parameters (%s): geen string-formatting van invoer in de SQL.
# Het filter `&&` gebruikt de GiST-index op kaart_pand.geom; ST_AsMVTGeom knipt en
# schaalt naar het tegelstelsel; de vereenvoudiging komt vóór ST_AsMVTGeom.
TILE_SQL = """
WITH env AS (
    SELECT ST_TileEnvelope(%(z)s, %(x)s, %(y)s,
                           ST_MakeEnvelope(%(minx)s, %(miny)s, %(maxx)s, %(maxy)s, 28992)) AS geom
),
mvt AS (
    SELECT p.gid, p.identificatie, p.bouwjaar, p.status, p.gebruiksdoel,
           ST_AsMVTGeom(
               CASE WHEN %(tol)s > 0
                    THEN ST_SimplifyPreserveTopology(p.geom, %(tol)s) ELSE p.geom END,
               env.geom, %(extent)s, %(buffer)s, true) AS geom
    FROM kaart_pand p, env
    WHERE p.geom && ST_Expand(
              env.geom, (ST_XMax(env.geom) - ST_XMin(env.geom)) * %(buffer)s / %(extent)s)
      AND ST_Area(p.geom) >= %(minarea)s
      AND (%(bj)s::int IS NULL OR p.bouwjaar >= %(bj)s::int)
)
SELECT ST_AsMVT(mvt.*, %(laag)s, %(extent)s, 'geom') FROM mvt
"""


def tegelbreedte(z: int) -> float:
    """Breedte van één tegel in meter op zoomniveau z (256 px x resolutie)."""
    return (GRID[2] - GRID[0]) / 2**z


def pixel_m(z: int) -> float:
    """Meter per schermpixel op zoomniveau z (tegel van 256 px)."""
    return tegelbreedte(z) / 256


def tolerantie(z: int, modus: str) -> tuple[float, float]:
    """(vereenvoudigingstolerantie in m, minimale oppervlakte in m2).

    'geen': de ruwe geometrie (alleen knippen en afronden door ST_AsMVTGeom).
    'topo': tolerantie een halve pixel, en panden kleiner dan 1 pixel^2 vallen weg.
    """
    if modus == "geen":
        return 0.0, 0.0
    return pixel_m(z) / 2, pixel_m(z) ** 2


def maak_tile(
    z: int, x: int, y: int, modus: str = "topo", bouwjaar_vanaf: int | None = None
) -> bytes:
    tol, minarea = tolerantie(z, modus)
    params = {
        "z": z,
        "x": x,
        "y": y,
        "minx": GRID[0],
        "miny": GRID[1],
        "maxx": GRID[2],
        "maxy": GRID[3],
        "tol": tol,
        "minarea": minarea,
        "extent": EXTENT,
        "buffer": BUFFER,
        "laag": LAAG,
        "bj": bouwjaar_vanaf,
    }
    with connection.cursor() as cursor:
        cursor.execute(TILE_SQL, params)
        rij = cursor.fetchone()
    return bytes(rij[0]) if rij and rij[0] else b""


@require_GET
@cache_control(public=True, max_age=CACHE_SECONDEN)
def panden_tile(request, z: int, x: int, y: int):
    if z > MAX_ZOOM or x >= 2**z or y >= 2**z:
        raise Http404("Tegel valt buiten het PDOK-grid (zoom 0-14).")
    modus = "geen" if request.GET.get("vereenvoudig") == "geen" else "topo"
    try:
        bj = int(request.GET["bouwjaar_vanaf"]) if "bouwjaar_vanaf" in request.GET else None
    except ValueError:
        return HttpResponse("bouwjaar_vanaf moet een geheel getal zijn.", status=400)
    # Zelf 16: elke parameter die de inhoud verandert hoort in de cache-sleutel
    sleutel = f"tile:{LAAG}:{modus}:{bj}:{z}:{x}:{y}"
    data = cache.get(sleutel)
    status = "HIT"
    if data is None:
        status = "MISS"
        data = maak_tile(z, x, y, modus, bj)
        cache.set(sleutel, data, CACHE_SECONDEN)
    antwoord = HttpResponse(data, content_type=CONTENT_TYPE)
    antwoord["X-Tile-Cache"] = status
    return antwoord
