"""Georefereren: lokale tekeningcoordinaten (m, SRID 990001) naar RD (EPSG:28992, m).

Paspunten
---------
Een paspunt is een punt dat je zowel in de tekening (lokaal x, y) als in de wereld (RD x, y)
kent, bv. een hoek van het BAG-pand. Uit paspunten volgt de transformatie.

Affien (6 parameters)
---------------------
    x_rd = a*x + b*y + c
    y_rd = d*x + e*y + f
Dit kan verschuiven, draaien, schalen (per as) en scheeftrekken. Elk paspunt levert 2
vergelijkingen (x_rd en y_rd); er zijn 6 onbekenden. ``numpy.linalg.lstsq`` zoekt de
parameters met de kleinste som van gekwadrateerde afstanden tussen berekende en gegeven RD.

Gelijkvormig (Helmert, 4 parameters)
------------------------------------
    x_rd = a*x - b*y + tx
    y_rd = b*x + a*y + ty
Alleen verschuiven, draaien en een schaal voor beide assen samen (a = s*cos(t), b = s*sin(t)).
Een tekening is meestal onvervormd; dan is Helmert genoeg en krijg je met dezelfde punten
meer controle (minder parameters).

Restfout en waarom >= 4 punten
------------------------------
Het residu van een punt is de afstand tussen de berekende en de opgegeven RD-positie; de
RMSE is wortel(som(residu^2) / aantal punten) in m. Bij 3 punten (niet op een lijn) zijn er 6
vergelijkingen voor 6 onbekenden: de affiene transformatie past dan exact, restfout 0, ook als
een punt fout is. Een restfout van 0 betekent dus NIET dat het goed is: er is geen controle.
Pas bij >= 4 punten blijft er overtollige informatie over (2 vergelijkingen per extra punt)
waarmee een fout punt zichtbaar wordt. Een fout verdeelt zich bij kleinste kwadraten wel
over alle punten, daarom geeft ``leave_one_out`` ook per punt: bereken zonder dat punt en meet
hoe ver het punt dan van zijn opgegeven RD ligt. Dat wijst de dader scherper aan.

Toepassen
---------
``pas_toe`` zet een Polygon in SRID 990001 om naar SRID 28992 met de matrix in Python
(GEOS-coordinaten). PostGIS kan dit ook: ``ST_Affine(geom, a, b, d, e, c, f)`` (2D-vorm,
x' = a*x + b*y + xoff, y' = d*x + e*y + yoff) met ``ST_SetSRID(..., 28992)``;
``pas_toe_postgis`` doet dat, zodat beide vergeleken kunnen worden.
"""

from dataclasses import dataclass
from math import atan2, degrees, hypot, sqrt

import numpy as np
from django.contrib.gis.geos import GEOSGeometry, LinearRing, Polygon
from django.db import connection

RD_SRID = 28992


@dataclass
class Resultaat:
    soort: str  # "affien" of "helmert"
    matrix: tuple[float, float, float, float, float, float]  # a, b, c, d, e, f
    residuen: list[float]  # m, per punt
    leave_one_out: list[float | None]  # m, None bij te weinig punten
    rmse: float
    rotatie_graden: float
    schaal_x: float
    schaal_y: float
    verschuiving: tuple[float, float]  # RD van lokaal (0, 0)

    @property
    def schaal(self) -> float:
        return (self.schaal_x + self.schaal_y) / 2

    def punt(self, x: float, y: float) -> tuple[float, float]:
        a, b, c, d, e, f = self.matrix
        return a * x + b * y + c, d * x + e * y + f


def _punten(paspunten) -> tuple[np.ndarray, np.ndarray]:
    lokaal = np.array([p["lokaal"] for p in paspunten], dtype=float)
    rd = np.array([p["rd"] for p in paspunten], dtype=float)
    return lokaal, rd


def _fit(lokaal: np.ndarray, rd: np.ndarray, soort: str) -> tuple[float, ...]:
    """Kleinste kwadraten. Eerst naar zwaartepunt schuiven: RD-getallen (1e5) naast lokale
    (1e1) maken de matrix slecht geconditioneerd."""
    n = len(lokaal)
    minimum = 3 if soort == "affien" else 2
    if n < minimum:
        raise ValueError(f"{soort}: minstens {minimum} paspunten nodig, kreeg {n}")
    ml, mr = lokaal.mean(axis=0), rd.mean(axis=0)
    x, y = (lokaal - ml).T
    u, v = (rd - mr).T
    if soort == "affien":
        A = np.column_stack([x, y, np.ones(n)])
        (a, b, _), *_ = np.linalg.lstsq(A, u, rcond=None)
        (d, e, _), *_ = np.linalg.lstsq(A, v, rcond=None)
    else:
        # onbekenden a, b, (tx, ty weg door centreren): u = a x - b y ; v = b x + a y
        A = np.vstack([np.column_stack([x, -y]), np.column_stack([y, x])])
        (a, b), *_ = np.linalg.lstsq(A, np.concatenate([u, v]), rcond=None)
        a, b, d, e = a, -b, b, a
    c = mr[0] - a * ml[0] - b * ml[1]
    f = mr[1] - d * ml[0] - e * ml[1]
    return a, b, c, d, e, f


def bereken(paspunten, soort: str = "affien") -> Resultaat:
    """Schat de transformatie uit ``paspunten`` ([{naam, lokaal:[x,y] m, rd:[x,y] m}, ...])."""
    lokaal, rd = _punten(paspunten)
    m = _fit(lokaal, rd, soort)
    a, b, c, d, e, f = m
    voorspeld = np.column_stack(
        [a * lokaal[:, 0] + b * lokaal[:, 1] + c, d * lokaal[:, 0] + e * lokaal[:, 1] + f]
    )
    res = np.hypot(*(voorspeld - rd).T)
    loo: list[float | None] = []
    minimum = 3 if soort == "affien" else 2
    for i in range(len(lokaal)):
        if len(lokaal) - 1 < minimum:
            loo.append(None)  # te weinig punten over om te schatten
            continue
        rest = np.delete(np.arange(len(lokaal)), i)
        a2, b2, c2, d2, e2, f2 = _fit(lokaal[rest], rd[rest], soort)
        px = a2 * lokaal[i, 0] + b2 * lokaal[i, 1] + c2
        py = d2 * lokaal[i, 0] + e2 * lokaal[i, 1] + f2
        loo.append(float(hypot(px - rd[i, 0], py - rd[i, 1])))
    return Resultaat(
        soort=soort,
        matrix=tuple(float(w) for w in m),
        residuen=[float(r) for r in res],
        leave_one_out=loo,
        rmse=float(sqrt(np.mean(res**2))),
        rotatie_graden=degrees(atan2(d, a)),
        schaal_x=hypot(a, d),
        schaal_y=hypot(b, e),
        verschuiving=(c, f),
    )


def pas_toe(poly: Polygon, matrix) -> Polygon:
    """Polygon (990001) -> Polygon (28992) met GEOS-coordinaten in Python."""
    a, b, c, d, e, f = matrix

    def ring(r):
        return LinearRing([(a * x + b * y + c, d * x + e * y + f) for x, y in r.coords])

    ringen = [ring(r) for r in poly]
    return Polygon(*ringen, srid=RD_SRID)


def pas_toe_postgis(poly: Polygon, matrix) -> Polygon:
    """Hetzelfde met PostGIS ``ST_Affine`` (2D-vorm: a, b, d, e, xoff, yoff)."""
    a, b, c, d, e, f = matrix
    with connection.cursor() as cur:
        cur.execute(
            "SELECT ST_AsEWKB(ST_SetSRID(ST_Affine(ST_GeomFromEWKB(%s), %s, %s, %s, %s, %s, %s),"
            " %s))",
            [bytes(poly.ewkb), a, b, d, e, c, f, RD_SRID],
        )
        return GEOSGeometry(memoryview(cur.fetchone()[0]))
