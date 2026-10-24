#!/usr/bin/env python3
"""RCS-laagcontrole + ruimtelijst via COM (pywin32) op een DRAAIENDE AutoCAD. Alleen Windows.

⚠️ Niet uitgevoerd tegen AutoCAD: de lesmaker heeft alleen een Mac. Wel gedraaid op de Mac: de guard
(uitvoer/com-guard-mac.txt). De COM-namen (GetActiveObject, ModelSpace, ObjectName, Area, Closed,
TextString, InsertionPoint) komen uit kennis van het AutoCAD ActiveX-objectmodel, niet uit een
geverifieerde bron in deze run.

Regels gelijk aan python-ezdxf/rcs_check.py (zonder shapely-controles op overlap en ongeldige geometrie).
Verschil met ezdxf en LISP: Polyline.Area komt van AutoCAD zelf en neemt bulges mee.
Gebruik (Windows, AutoCAD open met de tekening actief):  py rcs_check_com.py
"""

import re
import sys

RUIMTELAAG = "92 Rust- en werkgebieden"
LAAG_RE = re.compile(r"^[0-9]{2} [A-Za-z0-9 _-]+$")
UITGEZONDERD = {"0", "defpoints"}


def main():
    if sys.platform != "win32":
        print(
            f"rcs_check_com.py: gestopt, COM naar AutoCAD bestaat alleen op Windows (sys.platform = '{sys.platform}'). "
            "Gebruik op deze machine python-ezdxf/rcs_check.py."
        )
        return 2
    import win32com.client  # pywin32; pas na de guard importeren

    acad = win32com.client.GetActiveObject("AutoCAD.Application")  # AutoCAD moet draaien
    doc = acad.ActiveDocument
    msp = doc.ModelSpace
    fouten = 0
    print(f"RCSCHECK (COM) op {doc.Name}")
    per_laag = {}
    ruimten, nummers = [], []
    for e in msp:
        per_laag[e.Layer] = per_laag.get(e.Layer, 0) + 1
        if e.Layer == "0" and e.ObjectName != "AcDbBlockReference":
            print(f"FOUT laag 0 bevat {e.ObjectName} (handle {e.Handle})")
            fouten += 1
        if e.Layer == RUIMTELAAG and e.ObjectName == "AcDbPolyline":
            ruimten.append(e)
        if (
            e.Layer == RUIMTELAAG
            and e.ObjectName == "AcDbText"
            and re.match(r"^[0-9]{2}\.[0-9]{2}$", e.TextString)
        ):
            nummers.append((e.TextString, tuple(e.InsertionPoint)))
    print("-- Laagnamen en lege lagen --")
    for laag in doc.Layers:
        if laag.Name.lower() in UITGEZONDERD:
            continue
        if not LAAG_RE.match(laag.Name):
            print(f"FOUT laagnaam: '{laag.Name}'")
            fouten += 1
        if per_laag.get(laag.Name, 0) == 0:
            print(f"FOUT lege laag: '{laag.Name}'")
            fouten += 1
    print("-- Ruimtelijst (laag 92) --")
    print("nummer;handle;gesloten;opp_m2")
    for pl in ruimten:
        coords = list(pl.Coordinates)
        pts = list(zip(coords[0::2], coords[1::2], strict=True))
        gev = [nr for nr, p in nummers if _binnen(p, pts)]
        nr = gev[0] if len(gev) == 1 else "?"
        if len(gev) != 1:
            print(f"FOUT ruimte {pl.Handle}: {len(gev)} ruimtenummers in contour")
            fouten += 1
        if pl.Closed:
            print(f"{nr};{pl.Handle};ja;{pl.Area / 1e6:.2f}")
        else:
            print(f"FOUT ruimte {pl.Handle} ({nr}): polyline niet gesloten")
            fouten += 1
            print(f"{nr};{pl.Handle};nee;")
    print(f"Klaar: {fouten} bevinding(en), {len(ruimten)} ruimtecontour(en) op laag 92.")
    return 0


def _binnen(p, pts):
    x, y = p[0], p[1]
    res, j = False, len(pts) - 1
    for i, (xi, yi) in enumerate(pts):
        xj, yj = pts[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            res = not res
        j = i
    return res


if __name__ == "__main__":
    sys.exit(main())
