"""Een DXF importeren: ruimtecontouren naar ``Ruimte``-rijen in het lokale stelsel (SRID 990001).

Stappen (alles in een ``transaction.atomic``):

1. ``$INSUNITS`` lezen; 0 of afwezig -> weigeren (``ImportFout``), want dan weten we de schaal niet.
2. INSERT's exploderen met ``virtual_entities()``; wat erin zat komt in het rapport.
3. Ruimtes zoeken: LWPOLYLINE op een laag die met "92 " begint. Bulges worden afgevlakt
   (``boog_tolerantie_m`` = maximale afstand boog-koorde); het oppervlakteverschil staat in
   het rapport.
   Open polylijn met gat <= ``sluit_tolerantie_m``: sluiten en melden; anders overslaan en melden.
4. TEXT/MTEXT op laag "92 ..." geven nummer (``NN.NN``) en naam via punt-in-polygoon.
5. Opslaan met ``geometrie_ongeldig`` = niet GEOS ``valid``. Verder geen validiteits- of
   overlapcontrole (dat is les 19).
"""

import re
from collections import Counter
from math import atan, dist, sin

import ezdxf
from django.contrib.gis.geos import Polygon
from django.db import transaction
from ezdxf import DXFError, DXFStructureError, recover, units
from ezdxf.document import Drawing
from ezdxf.math import Vec2, is_point_in_polygon_2d
from ezdxf.path import make_path

from . import dxf
from .models import LOKAAL_SRID, Ruimte, Tekening

NUMMER = re.compile(r"^\d{2}\.\d{2}$")
RCS_LAAG = re.compile(r"^\d{2} ")
BAG_ID = re.compile(r"\b(\d{16})\b")


class ImportFout(Exception):
    """De DXF wordt geweigerd; er is niets opgeslagen."""


def _eenheid(doc: Drawing) -> tuple[str, float]:
    code = doc.header.get("$INSUNITS", 0)
    if not code:
        raise ImportFout("$INSUNITS ontbreekt of is 0: de eenheid is onbekend, import geweigerd")
    return units.decode(code), units.conversion_factor(code, units.M)


def _vlak_exact(punten: list[tuple[float, float, float]]) -> float:
    """Exacte oppervlakte (|shoelace| + cirkelsegmenten) van een gesloten polylijn met bulges."""
    totaal = 0.0
    n = len(punten)
    for i in range(n):
        x1, y1, b = punten[i]
        x2, y2, _ = punten[(i + 1) % n]
        totaal += (x1 * y2 - x2 * y1) / 2
        if b:
            hoek = 4 * atan(abs(b))
            straal = dist((x1, y1), (x2, y2)) / (2 * sin(hoek / 2))
            segment = straal**2 / 2 * (hoek - sin(hoek))
            totaal += segment if b > 0 else -segment
    return abs(totaal)


def _ring(pl, boog_tol_eenh: float) -> list[tuple[float, float]]:
    """Hoekpunten van de polylijn; bogen worden afgevlakt tot lijnstukken."""
    if any(p[4] for p in pl.get_points("xyseb")):
        return [(v.x, v.y) for v in make_path(pl).flattening(boog_tol_eenh)]
    return [(x, y) for x, y, _ in dxf.polylijn_punten(pl)]


def _entiteiten(msp, rapport: dict):
    """Modelspace-entiteiten, met INSERT's geexplodeerd (virtual_entities)."""
    for e in msp:
        if e.dxftype() != "INSERT":
            yield e
            continue
        inhoud = Counter(v.dxftype() for v in e.virtual_entities())
        rapport["inserts"].append(
            {
                "block": e.dxf.name,
                "laag": e.dxf.layer,
                "inhoud": dict(inhoud),
                "attributen": {a.dxf.tag: a.dxf.text for a in e.attribs},
            }
        )
        yield from e.virtual_entities()


def _tekstpunt(e) -> tuple[Vec2, str]:
    if e.dxftype() == "MTEXT":
        return Vec2(e.dxf.insert), e.plain_text().strip()
    d = e.dxf
    uitgelijnd = d.hasattr("align_point") and (d.get("halign", 0) or d.get("valign", 0))
    return Vec2(d.align_point if uitgelijnd else d.insert), d.text.strip()


def importeer_dxf(
    pad, tekening: Tekening, boog_tolerantie_m: float = 0.001, sluit_tolerantie_m: float = 0.05
) -> dict:
    """Importeer ``pad`` in ``tekening``; geef het rapport (ook in ``tekening.rapport``)."""
    try:
        try:
            doc = ezdxf.readfile(pad)
        except DXFStructureError:
            # Kapot bestand: ezdxf.recover repareert wat het kan (en negeert de rest).
            doc, _auditor = recover.readfile(pad)
    except (OSError, DXFError) as fout:
        raise ImportFout(f"Kan {pad} niet lezen: {fout}") from fout
    eenheid, m_per_u = _eenheid(doc)
    boog_tol = boog_tolerantie_m / m_per_u
    sluit_tol = sluit_tolerantie_m / m_per_u
    r = {
        "bestand": str(pad),
        "eenheid": eenheid,
        "meter_per_eenheid": m_per_u,
        "boog_tolerantie_m": boog_tolerantie_m,
        "sluit_tolerantie_m": sluit_tolerantie_m,
        "inserts": [],
        "gesloten_gemeld": [],
        "overgeslagen": [],
        "genegeerd": [],
        "zonder_nummer": [],
        "ongeldig": [],
        "ruimtes": [],
    }
    contouren, teksten, bag = [], [], ""
    for e in _entiteiten(doc.modelspace(), r):
        t = e.dxftype()
        laag = e.dxf.layer
        if t in ("TEXT", "MTEXT"):
            punt, tekst = _tekstpunt(e)
            if laag.startswith("92 "):
                # Een MTEXT kan nummer en naam op aparte regels hebben.
                teksten.extend(
                    (punt, regel.strip()) for regel in tekst.splitlines() if regel.strip()
                )
            elif m := BAG_ID.search(tekst):
                bag = bag or m.group(1)
        elif t == "LWPOLYLINE":
            if laag.startswith("92 "):
                contouren.append(e)
            elif not RCS_LAAG.match(laag) and laag not in ("0", "Defpoints"):
                r["genegeerd"].append(
                    {"laag": laag, "punten": len(e), "reden": "laagnaam voldoet niet aan '92 ...'"}
                )

    bouw = []
    for pl in contouren:
        punten = dxf.polylijn_punten(pl)
        if not pl.closed:
            gat = dist(punten[0][:2], punten[-1][:2])
            info = {"laag": pl.dxf.layer, "punten": len(punten), "gat_m": round(gat * m_per_u, 3)}
            if gat > sluit_tol:
                r["overgeslagen"].append(info | {"reden": "open, gat groter dan tolerantie"})
                continue
            r["gesloten_gemeld"].append(info)
        ring = _ring(pl, boog_tol)
        bulge = any(p[2] for p in punten)
        poly = Polygon([(x * m_per_u, y * m_per_u) for x, y in [*ring, ring[0]]], srid=LOKAAL_SRID)
        bouw.append((pl, ring, poly, bulge, punten))

    gebruikt = set()
    for pl, ring, poly, bulge, punten in bouw:
        binnen = [
            (i, tekst)
            for i, (p, tekst) in enumerate(teksten)
            if is_point_in_polygon_2d(p, [Vec2(x, y) for x, y in ring]) >= 0
        ]
        gebruikt.update(i for i, _ in binnen)
        nummers = [t for _, t in binnen if NUMMER.match(t)]
        namen = [t for _, t in binnen if not NUMMER.match(t)]
        item = {
            "nummer": nummers[0] if nummers else "",
            "naam": " ".join(namen),
            "laag": pl.dxf.layer,
            "oppervlakte_m2": round(poly.area, 3),
            "ongeldig": not poly.valid,
        }
        if bulge:
            exact = _vlak_exact(punten) * m_per_u**2
            item["bulge"] = {
                "exact_m2": round(exact, 6),
                "afgevlakt_m2": round(poly.area, 6),
                "verschil_m2": round(poly.area - exact, 6),
            }
        if not item["nummer"]:
            r["zonder_nummer"].append(item["naam"] or "(geen tekst)")
        if item["ongeldig"]:
            r["ongeldig"].append(item["nummer"] or item["naam"])
        r["ruimtes"].append(item | {"_poly": poly})

    r["teksten_buiten_ruimte"] = [t for i, (_, t) in enumerate(teksten) if i not in gebruikt]
    r["pand"] = bag
    with transaction.atomic():
        Ruimte.objects.filter(tekening=tekening).delete()
        for item in r["ruimtes"]:
            Ruimte.objects.create(
                tekening=tekening,
                nummer=item["nummer"],
                naam=item["naam"],
                laag=item["laag"],
                oppervlakte_m2=item["oppervlakte_m2"],
                geom=item["_poly"],
                geometrie_ongeldig=item["ongeldig"],
            )
            del item["_poly"]
        r["aantal_ruimtes"] = len(r["ruimtes"])
        r["totaal_m2"] = round(sum(i["oppervlakte_m2"] for i in r["ruimtes"]), 3)
        tekening.eenheid = eenheid
        tekening.rapport = r
        if bag and not tekening.bag_pand_id:
            tekening.bag_pand_id = bag
        tekening.save()
    return r
