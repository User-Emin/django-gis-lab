#!/usr/bin/env python3
"""RCS-laagcontrole + ruimtelijst zonder AutoCAD (ezdxf). Referentie voor de LISP-, .NET- en COM-versie.

Gebruik: uv run python autocad/python-ezdxf/rcs_check.py <tekening.dxf> [uitvoer.csv] [--json]

--json: alleen een JSON-object op stdout (bestand, bevindingen, ruimten, aantal_bevindingen); exit 1 bij bevindingen.

Zelfde regels als lisp/rcs-check.lsp:
- laagnaam: 2 cijfers + spatie + omschrijving (A-Z a-z 0-9 spatie - _), laag 0 en Defpoints uitgezonderd
- lege laag: geen entiteiten in modelspace (0 en Defpoints uitgezonderd)
- laag 0: alleen INSERT
- ruimtelijst: elke LWPOLYLINE op "92 Rust- en werkgebieden"; nummer = TEXT "##.##" op die laag waarvan
  het invoegpunt (groep 10) binnen de contour ligt; oppervlakte zonder bulge (shoelace, zoals LISP) en met bulge.

Extra, alleen in deze Python-versie (shapely/GEOS), BEWUST NIET in de LISP- en .NET-versie:
- ruimten die elkaar overlappen (overlap in m2)
- ongeldige of zichzelf snijdende geometrie (is_valid / explain_validity), bv. een bowtie
"""

import csv
import json
import math
import re
import sys
from collections import Counter

import ezdxf
from shapely.geometry import Polygon
from shapely.validation import explain_validity

RUIMTELAAG = "92 Rust- en werkgebieden"
LAAG_RE = re.compile(r"^[0-9]{2} [A-Za-z0-9 _-]+$")
NR_RE = re.compile(r"^[0-9]{2}\.[0-9]{2}$")
UITGEZONDERD = {"0", "defpoints"}


def shoelace(pts):
    """Getekende oppervlakte (mm2) van de koordenveelhoek; bulges genegeerd."""
    n = len(pts)
    return (
        sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n)) / 2
    )


def met_bulge(pts, bulges):
    """Shoelace + exacte cirkelsegmenten: segment = r^2/2 * (theta - sin theta), theta = 4*atan(b)."""
    a = shoelace(pts)
    n = len(pts)
    for i, b in enumerate(bulges):
        if not b:
            continue
        (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % n]
        c = math.hypot(x2 - x1, y2 - y1)
        th = 4 * math.atan(abs(b))
        r = c / (2 * math.sin(th / 2))
        a += math.copysign(r * r / 2 * (th - math.sin(th)), b)
    return a


def binnen(p, pts):
    """Ray casting: ligt punt p binnen de veelhoek pts?"""
    x, y = p
    res = False
    j = len(pts) - 1
    for i in range(len(pts)):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            res = not res
        j = i
    return res


def controleer(pad):
    doc = ezdxf.readfile(pad)
    msp = doc.modelspace()
    regels, fouten = [], 0
    regels.append(f"RCSCHECK (ezdxf {ezdxf.__version__}) op {pad.split('/')[-1]}")
    per_laag = Counter(e.dxf.layer for e in msp)
    regels.append("-- Laagnamen en lege lagen --")
    for laag in doc.layers:
        naam = laag.dxf.name
        if naam.lower() in UITGEZONDERD:
            continue
        if not LAAG_RE.match(naam):
            regels.append(f"FOUT laagnaam: '{naam}' voldoet niet aan '## omschrijving'")
            fouten += 1
        if per_laag[naam] == 0:
            regels.append(f"FOUT lege laag: '{naam}'")
            fouten += 1
    regels.append("-- Laag 0 --")
    for e in msp.query('*[layer=="0"]'):
        if e.dxftype() != "INSERT":
            regels.append(f"FOUT laag 0 bevat {e.dxftype()} (handle {e.dxf.handle})")
            fouten += 1
    nummers = [
        (e.dxf.text, (e.dxf.insert.x, e.dxf.insert.y))
        for e in msp.query(f'TEXT[layer=="{RUIMTELAAG}"]')
        if NR_RE.match(e.dxf.text)
    ]
    regels.append("-- Ruimtelijst (laag 92) --")
    regels.append("nummer;handle;gesloten;opp_m2_zonder_bulge;opp_m2_met_bulge")
    rijen = []
    polys = []  # (nummer, handle, shapely-polygoon) van gesloten contouren
    for e in msp.query(f'LWPOLYLINE[layer=="{RUIMTELAAG}"]'):
        xyb = [(p[0], p[1], p[4]) for p in e.get_points("xyseb")]
        pts = [(x, y) for x, y, _ in xyb]
        bul = [b for _, _, b in xyb]
        if not e.closed:
            bul[-1] = 0.0  # bulge van het laatste punt telt alleen bij een gesloten polyline
        gevonden = [nr for nr, p in nummers if binnen(p, pts)]
        nr = gevonden[0] if len(gevonden) == 1 else ("?" if not gevonden else "+".join(gevonden))
        if nr == "?" or "+" in nr:
            regels.append(f"FOUT ruimte {e.dxf.handle}: {len(gevonden)} ruimtenummers in contour")
            fouten += 1
        if e.closed:
            polys.append((nr, e.dxf.handle, Polygon(pts)))
            a0 = abs(shoelace(pts)) / 1e6
            a1 = abs(met_bulge(pts, bul)) / 1e6
            rij = [nr, e.dxf.handle, "ja", f"{a0:.2f}", f"{a1:.2f}"]
        else:
            regels.append(f"FOUT ruimte {e.dxf.handle} ({nr}): polyline niet gesloten")
            fouten += 1
            rij = [nr, e.dxf.handle, "nee", "", ""]
        rijen.append(rij)
        regels.append(";".join(rij))
    regels.append("-- Ongeldige geometrie (shapely is_valid; niet in LISP/.NET) --")
    for nr, h, pg in polys:
        if not pg.is_valid:
            regels.append(
                f"FOUT ongeldige geometrie {nr} ({h}): {explain_validity(pg)}; "
                f"echte oppervlakte onbetrouwbaar (shoelace-waarde telt niet)"
            )
            fouten += 1
    regels.append("-- Overlappende ruimten (shapely intersection; niet in LISP/.NET) --")
    for i in range(len(polys)):
        for j in range(i + 1, len(polys)):
            a, b = polys[i], polys[j]
            if not (a[2].is_valid and b[2].is_valid):
                continue  # intersectie van ongeldige geometrie is niet betrouwbaar
            m2 = a[2].intersection(b[2]).area / 1e6
            if m2 > 0.001:
                regels.append(f"FOUT overlap {a[0]} ({a[1]}) / {b[0]} ({b[1]}): {m2:.2f} m2")
                fouten += 1
    regels.append(f"Klaar: {fouten} bevinding(en), {len(rijen)} ruimtecontour(en) op laag 92.")
    tekst = "\n".join(regels)
    regels.append("-- Overzicht tegen fouten.md (alleen zinvol voor plattegrond-bg-fouten.dxf) --")
    for nr_, naam, patroon in [
        (1, "00.04 niet gesloten", "polyline niet gesloten"),
        (2, "00.03 overlapt 00.02", "FOUT overlap"),
        (3, "laagnaam 'Ruimten'", "FOUT laagnaam"),
        (4, "ruimte zonder nummer (00.11)", "0 ruimtenummers"),
        (5, "bowtie 00.06 ongeldig", "FOUT ongeldige geometrie"),
    ]:
        regels.append(f"fout {nr_} ({naam}): {'GEVONDEN' if patroon in tekst else 'niet gevonden'}")
    regels.append(
        "NB: LISP- en .NET-versie doen controle 2 (overlap) en 5 (is_valid) BEWUST NIET; "
        "Python + shapely/GEOS doet dit goedkoop (lesargument)."
    )
    return regels, rijen


def als_json(pad, regels, rijen):
    """Machineleesbare vorm (voor CI): bevindingen = de FOUT-regels, ruimten = de CSV-rijen."""
    kop = ["nummer", "handle", "gesloten", "opp_m2_zonder_bulge", "opp_m2_met_bulge"]
    bevindingen = [r for r in regels if r.startswith("FOUT")]
    return {
        "bestand": pad.split("/")[-1],
        "aantal_bevindingen": len(bevindingen),
        "bevindingen": bevindingen,
        "ruimten": [dict(zip(kop, rij, strict=True)) for rij in rijen],
    }


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--json"]
    json_modus = "--json" in sys.argv[1:]
    if not args:
        sys.exit("gebruik: rcs_check.py <tekening.dxf> [uitvoer.csv] [--json]")
    regels, rijen = controleer(args[0])
    if json_modus:
        uit = als_json(args[0], regels, rijen)
        print(json.dumps(uit, ensure_ascii=False, indent=2))
    else:
        print("\n".join(regels))
    if len(args) > 1:
        with open(args[1], "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["nummer", "handle", "gesloten", "opp_m2_zonder_bulge", "opp_m2_met_bulge"])
            w.writerows(rijen)
    if json_modus and uit["aantal_bevindingen"]:
        sys.exit(1)
