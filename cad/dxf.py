"""Een DXF lezen met ezdxf: kleine functies, elk met een duidelijke taak.

Een DXF-bestand heeft vier delen die wij hier gebruiken:

* HEADER   - variabelen als ``$INSUNITS`` (``doc.header``)
* TABLES   - lagen, linetypes, stijlen (``doc.layers``)
* BLOCKS   - herbruikbare tekeningdelen (``doc.blocks``)
* ENTITIES - de tekening zelf (``doc.modelspace()``)

De functies hieronder werken op een ``Drawing`` (``doc``) of op de modelspace (``msp``)
en geven gewone Python-structuren terug, zodat ze zonder database te testen zijn.
"""

from collections import Counter
from dataclasses import dataclass
from math import degrees

from ezdxf import bbox, units
from ezdxf.document import Drawing
from ezdxf.layouts import Modelspace
from ezdxf.math import Vec2, bulge_to_arc, is_point_in_polygon_2d
from ezdxf.math import area as vlakte

RUIMTELAAG = "92 Rust- en werkgebieden"
LABELBLOCK = "RUIMTELABEL"


def header_variabelen(doc: Drawing) -> dict:
    """De HEADER-variabelen die voor georeferentie en eenheden tellen."""
    h = doc.header
    return {naam: h.get(naam) for naam in ("$ACADVER", "$INSUNITS", "$MEASUREMENT", "$LUNITS")} | {
        "$EXTMIN": tuple(h.get("$EXTMIN")),
        "$EXTMAX": tuple(h.get("$EXTMAX")),
    }


def extents(doc: Drawing) -> tuple[tuple, tuple]:
    """Werkelijke omhullende. $EXTMIN/$EXTMAX staan soms op 1e+20 (niet berekend)."""
    kader = bbox.extents(doc.modelspace())
    return tuple(kader.extmin), tuple(kader.extmax)


def eenheid_naam(doc: Drawing) -> str:
    """``$INSUNITS`` als woord: 4 -> 'mm'. 0 betekent 'niet opgegeven'."""
    return units.decode(doc.header.get("$INSUNITS", 0)) or "onbekend"


def meter_per_unit(doc: Drawing) -> float:
    """Hoeveel meter is 1 tekeneenheid? Bij ``$INSUNITS`` = 4 (mm) is dat 0,001."""
    code = doc.header.get("$INSUNITS", 0)
    if code == 0:
        raise ValueError("$INSUNITS = 0: de eenheid is niet opgegeven, dan weet je het niet")
    return units.conversion_factor(code, units.M)


def lagen(doc: Drawing) -> list[dict]:
    """TABLES: per laag naam, kleurnummer, linetype, aan/uit en bevroren."""
    return [
        {
            "naam": laag.dxf.name,
            "kleur": laag.dxf.color,
            "linetype": laag.dxf.linetype,
            "aan": laag.is_on(),
            "bevroren": laag.is_frozen(),
        }
        for laag in doc.layers
    ]


def ongebruikte_lagen(doc: Drawing) -> list[str]:
    """Lagen waar geen enkele entiteit in de modelspace op staat (Zelf, les 17)."""
    gebruikt = {e.dxf.layer for e in doc.modelspace()}
    return [laag["naam"] for laag in lagen(doc) if laag["naam"] not in gebruikt]


def blocks(doc: Drawing) -> dict[str, list[str]]:
    """BLOCKS: naam -> tags van de ATTDEFs. Systeemblocks (*Model_Space, *D1) blijven weg."""
    return {
        b.name: [a.dxf.tag for a in b.query("ATTDEF")]
        for b in doc.blocks
        if not b.name.startswith("*") and not b.name.startswith("_")
    }


def tel_entiteiten(msp: Modelspace) -> Counter:
    """ENTITIES: aantal per (dxftype, laag)."""
    return Counter((e.dxftype(), e.dxf.layer) for e in msp)


def bulge_naar_boog(p1, p2, bulge: float) -> dict:
    """Een LWPOLYLINE-segment met bulge is een cirkelboog.

    ``bulge = tan(hoek / 4)``: 0 is recht, 1 is een halve cirkel, negatief is met de klok mee.
    ``ezdxf.math.bulge_to_arc`` rekent middelpunt, hoeken (radialen) en straal uit.
    """
    middelpunt, start, einde, straal = bulge_to_arc(p1[:2], p2[:2], bulge)
    return {
        "middelpunt": (round(float(middelpunt.x), 1), round(float(middelpunt.y), 1)),
        "straal": round(float(straal), 1),
        "start_graden": round(float(degrees(start)), 1),
        "eind_graden": round(float(degrees(einde)), 1),
    }


def polylijn_punten(e) -> list[tuple[float, float, float]]:
    """Punten van een LWPOLYLINE als (x, y, bulge)."""
    return [(p[0], p[1], p[4]) for p in e.get_points("xyseb")]


def oppervlakte(e, doc: Drawing) -> float:
    """Oppervlakte van een gesloten polylijn in m2, rekening houdend met ``$INSUNITS``."""
    xy = [(x, y) for x, y, _ in polylijn_punten(e)]
    return float(vlakte(xy)) * meter_per_unit(doc) ** 2


@dataclass
class Ruimte:
    nummer: str
    functie: str
    oppervlak_m2: float
    punten: int


def ruimtes(doc: Drawing) -> list[Ruimte]:
    """Koppel elke gesloten polylijn op de ruimtelaag aan het ruimtelabel (INSERT) erin.

    Punt-in-polygoon is simpel: ``ezdxf.math.is_point_in_polygon_2d`` (geen GEOS nodig).
    Een bulge in een ruimtecontour wordt hier genegeerd; de ruimtes in deze tekening zijn
    rechthoeken. Volgende les doet dit met echte geometrie in PostGIS.
    """
    msp = doc.modelspace()
    labels = [
        (e.dxf.insert, {a.dxf.tag: a.dxf.text for a in e.attribs})
        for e in msp.query(f'INSERT[name=="{LABELBLOCK}"]')
    ]
    gevonden = []
    for pl in msp.query(f'LWPOLYLINE[layer=="{RUIMTELAAG}"]'):
        if not pl.is_closed:
            continue
        xy = [Vec2(x, y) for x, y, _ in polylijn_punten(pl)]
        for punt, attribs in labels:
            if is_point_in_polygon_2d(Vec2(punt), xy) >= 0:  # 1 binnen, 0 rand, -1 buiten
                m2 = oppervlakte(pl, doc)
                gevonden.append(
                    Ruimte(attribs.get("RUIMTENR", ""), attribs.get("FUNCTIE", ""), m2, len(xy))
                )
                break
    return sorted(gevonden, key=lambda r: r.nummer)
