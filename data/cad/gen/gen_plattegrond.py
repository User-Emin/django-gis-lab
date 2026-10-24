#!/usr/bin/env python3
"""Genereert de oefenplattegrond (fictief) op de contour van BAG-pand 0034100000049762.

Gebruik: .venv/bin/python gen_plattegrond.py   (deterministisch; zelfde invoer = zelfde bytes)
Schrijft: plattegrond-bg.dxf, plattegrond-bg-fouten.dxf, pand.json, georef-waarheid.json, render/*.png
"""
import json, math, subprocess, csv, io
import tempfile
from pathlib import Path
import ezdxf
from ezdxf import const
from ezdxf.enums import TextEntityAlignment as TEA

HERE = Path(__file__).resolve().parent.parent  # uitvoer: data/cad/
PAND_ID = "0034100000049762"
GPKG = Path(__file__).resolve().parents[2] / "almere.gpkg"
BOUWLAAG = "00"

# --- 1. pand lezen (alleen lezen, kopie in bron/pand.gpkg) -------------------------------------
def lees_pand():
    pg = Path(tempfile.gettempdir()) / "pand-0034.gpkg"
    pg.unlink(missing_ok=True)
    if True:
        subprocess.run(["ogr2ogr", "-f", "GPKG", str(pg), str(GPKG), "panden", "-where",
                        f"identificatie='{PAND_ID}'", "-nln", "pand"], check=True)
    out = subprocess.run(["ogr2ogr", "-f", "CSV", "/vsistdout/", str(pg), "pand", "-lco", "GEOMETRY=AS_WKT"],
                         check=True, capture_output=True, text=True).stdout
    row = next(csv.DictReader(io.StringIO(out)))
    wkt = row["geom"]
    inner = wkt[wkt.index("(((") + 3: wkt.index(")))")]
    pts = [tuple(float(v) for v in p.split()[:2]) for p in inner.split(",")][:-1]
    return row, pts

row, RD = lees_pand()  # 6 hoekpunten: A B C D E F
A, B, C, D, E, F = RD
TH = math.atan2(C[1] - B[1], C[0] - B[0])          # richting BC in RD
ROT = -TH                                           # rotatie RD -> lokaal (radialen)
SHIFT = 500.0                                       # mm marge: B komt op (500, 500)

def rd2loc(p):
    dx, dy = (p[0] - B[0]) * 1000, (p[1] - B[1]) * 1000
    return (round(dx * math.cos(ROT) - dy * math.sin(ROT)) + SHIFT,
            round(dx * math.sin(ROT) + dy * math.cos(ROT)) + SHIFT)

def loc2rd(p):
    x, y = p[0] - SHIFT, p[1] - SHIFT
    return (B[0] + (x * math.cos(-ROT) - y * math.sin(-ROT)) / 1000,
            B[1] + (x * math.sin(-ROT) + y * math.cos(-ROT)) / 1000)

L = {k: rd2loc(v) for k, v in zip("ABCDEF", RD)}   # lokale contour (mm)
CONTOUR = [L[k] for k in "ABCDEF"]

def area(pts):
    return abs(sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
                   for i in range(len(pts)))) / 2

def offset_poly(pts, d):
    """Binnenwaarts verschuiven met mitre (polygon tegen de klok in)."""
    n, out = len(pts), []
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        def nrm(a, b):
            dx, dy = b[0] - a[0], b[1] - a[1]; l = math.hypot(dx, dy)
            return (-dy / l, dx / l)
        n1, n2 = nrm(p0, p1), nrm(p1, p2)
        bx, by = n1[0] + n2[0], n1[1] + n2[1]
        k = d / (1 + n1[0] * n2[0] + n1[1] * n2[1])
        out.append((p1[0] + bx * k, p1[1] + by * k))
    return out

# contour is A,B,C,D,E,F = rechtsom/linksom? zorg voor tegen de klok in
ccw = sum(CONTOUR[i][0] * CONTOUR[(i + 1) % 6][1] - CONTOUR[(i + 1) % 6][0] * CONTOUR[i][1] for i in range(6)) > 0
ORDER = "ABCDEF" if ccw else "AFEDCB"
CT = [L[k] for k in ORDER]
WALL = 300.0
INN = offset_poly(CT, WALL)
IDX = {k: i for i, k in enumerate(ORDER)}
iL = {k: INN[IDX[k]] for k in "ABCDEF"}
# bilineaire afbeelding nominale binnenruimte (0..NW x 0..NH) -> binnenkwadrant B' C' F' A'
NW = NH = 29000.0
def mp(x, y):
    u, v = x / NW, y / NH
    b, c, f, a = iL["B"], iL["C"], iL["F"], iL["A"]
    return tuple(round((1 - u) * (1 - v) * b[i] + u * (1 - v) * c[i] + u * v * f[i] + (1 - u) * v * a[i], 1) for i in (0, 1))

# --- 2. plattegrond-ontwerp (nominale coordinaten, mm) --------------------------------------------
RUIMTEN = [
    ("01", "Entree", 0, 0, 8000, 9000),
    ("02", "Kantoor", 8000, 0, 16000, 9000),
    ("03", "Vergaderruimte", 16000, 0, 23000, 9000),
    ("04", "Kantoor", 23000, 0, 29000, 9000),
    ("05", "Gang", 0, 9000, 29000, 12000),
    ("06", "Archief", 0, 12000, 7000, 20000),
    ("07", "Technische ruimte", 0, 20000, 7000, 29000),
    ("08", "Werkruimte", 7000, 12000, 19000, 29000),
    ("09", "Kantoor", 19000, 12000, 29000, 20500),
    ("10", "Toilet", 19000, 20500, 24000, 29000),
    ("11", "Pantry", 24000, 20500, 29000, 29000),
]
T = 200.0  # dikte binnenwand
# binnenwanden: (orientatie, lijn, van, tot)  [tot/van = vlak langs wandrichting, exclusief aansluitende wandvlakken]
BW = [("h", 9000, 0, 29000), ("h", 12000, 0, 29000), ("h", 20000, 0, 6900), ("h", 20500, 19100, 29000),
      ("v", 8000, 0, 8900), ("v", 16000, 0, 8900), ("v", 23000, 0, 8900),
      ("v", 7000, 12100, 29000), ("v", 19000, 12100, 29000), ("v", 24000, 20600, 29000)]
# deuren: (orientatie, lijn, start, zwaairichting)  breedte 900
DEUR = [("h", 9000, 3550, -1), ("h", 9000, 11550, -1), ("h", 9000, 19050, -1), ("h", 9000, 25550, -1),
        ("h", 12000, 3050, 1), ("h", 12000, 12550, 1), ("h", 12000, 23550, 1),
        ("v", 7000, 24050, 1), ("v", 19000, 23550, -1), ("h", 20500, 26050, -1)]
DW = 900.0

def geopend(o, lijn, a):
    return any(d[0] == o and d[1] == lijn and d[2] <= a < d[2] + DW for d in DEUR)

def wand_stukken(o, lijn, van, tot):
    gaten = sorted((d[2], d[2] + DW) for d in DEUR if d[0] == o and d[1] == lijn)
    pos, res = van, []
    for g0, g1 in gaten:
        if g0 > pos: res.append((pos, g0))
        pos = g1
    if pos < tot: res.append((pos, tot))
    return res

def bouw(fouten=False):
    doc = ezdxf.new("R2018", setup=False)
    h = doc.header
    h["$INSUNITS"] = 4; h["$MEASUREMENT"] = 1; h["$LUNITS"] = 2; h["$LWDISPLAY"] = 0; h["$CLAYER"] = "0"
    h["$FINGERPRINTGUID"] = "{00000000-0000-0000-0000-00000000E017}"
    h["$VERSIONGUID"] = "{00000000-0000-0000-0000-00000000E018}"
    for v in ("$TDCREATE", "$TDUCREATE", "$TDUPDATE", "$TDUUPDATE"):
        h[v] = 2461333.5
    h["$TDINDWG"] = 0.0; h["$TDUSRTIMER"] = 0.0
    lagen = {"21 Buitenwanden": 7, "22 Binnenwanden": 8, "31 Buitenwandopeningen": 3, "32 Binnenwandopeningen": 3,
             "92 Rust- en werkgebieden": 5, "99 Maatvoering": 6, "99 Tekst": 7}
    if fouten: lagen["Ruimten"] = 5
    for n, c in lagen.items(): doc.layers.add(n, color=c)
    msp = doc.modelspace()

    # block met attributen (in laag 0)
    blk = doc.blocks.new("RUIMTELABEL")
    blk.add_attdef("RUIMTENR", (0, 0), text=f"{BOUWLAAG}.00", dxfattribs={"height": 450, "layer": "0", "color": 5,
                   "align_point": (0, 0), "halign": 1, "valign": 2}, ).dxf.prompt = "Ruimtenummer"
    ad = blk.add_attdef("FUNCTIE", (0, -500), text="functie", dxfattribs={"height": 250, "layer": "0", "flags": 1,
                        "align_point": (0, -500), "halign": 1, "valign": 2})
    ad.dxf.prompt = "Functie"
    for a in blk.query("ATTDEF"):
        a.dxf.halign = 4; a.dxf.valign = 0; a.dxf.align_point = a.dxf.insert  # midden

    # buitenwanden: per zijde een strook (met deuropening aan zijde BC)
    def strook(ket_buiten, ket_binnen, la, ttot_a=None):
        pts = ket_buiten + ket_binnen[::-1]
        msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "21 Buitenwanden"})
        hch = msp.add_hatch(color=9, dxfattribs={"layer": "21 Buitenwanden"})
        hch.set_pattern_fill("ANSI31", scale=60)
        hch.paths.add_polyline_path(pts, is_closed=True)
    ring = ORDER
    kant = {}
    for i in range(6):
        kant.setdefault(ring[i] + ring[(i + 1) % 6], (L[ring[i]], L[ring[(i + 1) % 6]], iL[ring[i]], iL[ring[(i + 1) % 6]]))
    ZIJDEN = [["A", "B"], ["B", "C"], ["C", "D", "E", "F"], ["F", "A"]]
    for z in ZIJDEN:
        z = z if all(ring.index(z[i]) + 1 == ring.index(z[i + 1]) or (ring.index(z[i]) == 5 and ring.index(z[i + 1]) == 0)
                     for i in range(len(z) - 1)) else z[::-1]
        bu, bi = [L[k] for k in z], [iL[k] for k in z]
        if set(z) == {"B", "C"}:
            # deuropening hoofdingang: x 3500..4400 nominaal (vanaf binnenvlak B')
            b0, b1 = iL["B"][0] + 3550, iL["B"][0] + 3550 + 1200
            bt, bc = (L["B"], L["C"]) if z[0] == "B" else (L["C"], L["B"])
            for xa, xb in ((L["B"][0], b0), (b1, L["C"][0])):
                fa = lambda x, p, q: (x, p[1] + (q[1] - p[1]) * (x - p[0]) / (q[0] - p[0]))
                po = [fa(xa, L["B"], L["C"]), fa(xb, L["B"], L["C"]), fa(xb, iL["B"], iL["C"]), fa(xa, iL["B"], iL["C"])]
                msp.add_lwpolyline(po, close=True, dxfattribs={"layer": "21 Buitenwanden"})
                hch = msp.add_hatch(color=9, dxfattribs={"layer": "21 Buitenwanden"})
                hch.set_pattern_fill("ANSI31", scale=60); hch.paths.add_polyline_path(po, is_closed=True)
            y0 = L["B"][1]
            for xx in (b0, b1):
                msp.add_line((xx, y0), (xx, iL["B"][1]), dxfattribs={"layer": "31 Buitenwandopeningen"})
            # dubbele draaideur: bladlijn + zwaaiboog naar binnen
            msp.add_line((b0, iL["B"][1]), (b0, iL["B"][1] + 1200), dxfattribs={"layer": "31 Buitenwandopeningen"})
            msp.add_arc((b0, iL["B"][1]), 1200, 0, 90, dxfattribs={"layer": "31 Buitenwandopeningen"})
        else:
            strook(bu, bi, 0)

    # binnenwanden
    for o, lijn, van, tot in BW:
        for a, b in wand_stukken(o, lijn, van, tot):
            r = [(a, lijn - T / 2), (b, lijn - T / 2), (b, lijn + T / 2), (a, lijn + T / 2)] if o == "h" else \
                [(lijn - T / 2, a), (lijn + T / 2, a), (lijn + T / 2, b), (lijn - T / 2, b)]
            msp.add_lwpolyline([mp(*p) for p in r], close=True, dxfattribs={"layer": "22 Binnenwanden"})
    # deuren
    eerste_boog = True
    for o, lijn, a, s in DEUR:
        if o == "h":
            hinge, dicht, blad = (a, lijn), (a + DW, lijn), (a, lijn + s * DW)
        else:
            hinge, dicht, blad = (lijn, a), (lijn, a + DW), (lijn + s * DW, a)
        dx = {"layer": "32 Binnenwandopeningen"}
        msp.add_line(mp(*hinge), mp(*blad), dxfattribs=dx)
        if eerste_boog:  # LWPOLYLINE met bulge (kwartcirkel: tan(90/4))
            p1, p2 = mp(*dicht), mp(*blad)
            sign = 1 if ((dicht[0] - hinge[0]) * (blad[1] - hinge[1]) - (dicht[1] - hinge[1]) * (blad[0] - hinge[0])) > 0 else -1
            msp.add_lwpolyline([(p1[0], p1[1], 0, 0, sign * math.tan(math.radians(22.5))), (p2[0], p2[1], 0, 0, 0)], format="xyseb", dxfattribs=dx)
            eerste_boog = False
        else:
            c = mp(*hinge)
            ang = {("h", 1): (0, 90), ("h", -1): (270, 360), ("v", 1): (0, 90), ("v", -1): (90, 180)}[(o, s)]
            if o == "v": ang = {1: (0, 90), -1: (90, 180)}[s] if False else ((0, 90) if s == 1 else (90, 180))
            msp.add_arc(c, DW, ang[0], ang[1], dxfattribs=dx)

    # ruimten: gesloten LWPOLYLINE + block + TEXT
    teller = 0
    for code, functie, x0, y0, x1, y1 in RUIMTEN:
        nr = f"{BOUWLAAG}.{code}"
        ix0 = x0 + (T / 2 if x0 > 0 else 0); iy0 = y0 + (T / 2 if y0 > 0 else 0)
        ix1 = x1 - (T / 2 if x1 < NW else 0); iy1 = y1 - (T / 2 if y1 < NH else 0)
        # wanden zijn op de lijn gecentreerd; 'gang' sluit aan op wandvlakken
        pts = [(ix0, iy0), (ix1, iy0), (ix1, iy1), (ix0, iy1)]
        layer, sluit = "92 Rust- en werkgebieden", True
        if fouten:
            if code == "04": sluit = False                       # fout 1: niet gesloten
            if code == "03": pts[0] = (ix0 - 1500, iy0); pts[3] = (ix0 - 1500, iy1)  # fout 2: overlap met 02
            if code == "10": layer = "Ruimten"                   # fout 3: verkeerde laagnaam
            if code == "06": pts[2], pts[3] = pts[3], pts[2]     # fout 5: zelfdoorsnijding (bowtie)
        mpts = [mp(*p) for p in pts]
        if not sluit:
            msp.add_lwpolyline(mpts, close=False, dxfattribs={"layer": layer})
        else:
            msp.add_lwpolyline(mpts, close=True, dxfattribs={"layer": layer})
        cx, cy = mp((ix0 + ix1) / 2, (iy0 + iy1) / 2)
        geen_nr = fouten and code == "11"                          # fout 4: ruimte zonder nummer
        ins = msp.add_blockref("RUIMTELABEL", (cx, cy + 450), dxfattribs={"layer": "0"})
        ins.add_auto_attribs({"RUIMTENR": "" if geen_nr else nr, "FUNCTIE": functie})
        for at in ins.attribs: at.dxf.layer = "0"
        if not geen_nr:
            msp.add_text(nr, height=350, dxfattribs={"layer": "92 Rust- en werkgebieden", "color": 1, "style": "Standard"}).set_placement((cx, cy - 250), align=TEA.MIDDLE_CENTER)
        msp.add_text(functie, height=280, dxfattribs={"layer": "92 Rust- en werkgebieden", "color": 2, "style": "Standard"}).set_placement((cx, cy - 750), align=TEA.MIDDLE_CENTER)
        teller += 1

    # maatlijn (uitwendige maat zijde BC) en bouwlaagaanduiding
    dim = msp.add_linear_dim(base=(0, -1500), p1=L["B"], p2=L["C"], dimstyle="EZDXF",
                             override={"dimtxt": 300, "dimasz": 200, "dimexe": 100, "dimexo": 100, "dimdec": 0},
                             dxfattribs={"layer": "99 Maatvoering"})
    dim.render()
    msp.add_text(f"{BOUWLAAG} Begane grond - oefenplattegrond (fictief)", height=500, dxfattribs={"layer": "99 Tekst"}).set_placement((L["B"][0], -3000))
    msp.add_text(f"Pand {PAND_ID}", height=300, dxfattribs={"layer": "99 Tekst"}).set_placement((L["B"][0], -3600))
    return doc


def normaliseer(pad):
    """ezdxf zet bij opslaan tijdstempels en GUIDs; vast zetten voor deterministische bytes."""
    import re
    t = pad.read_text(encoding="utf-8")
    t = re.sub(r"\{[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}", "{00000000-0000-0000-0000-00000000E017}", t)
    t = re.sub(r"\n24613\d\d\.\d+", "\n2461333.5", t)
    t = re.sub(r"(\d+\.\d+\.\d+) @ \d{4}-\d\d-\d\dT[\d:.+]+", r"\1 @ 2026-10-24T00:00:00+00:00", t)
    pad.write_text(t, encoding="utf-8")


def schrijf():
    for fouten, naam in ((False, "plattegrond-bg.dxf"), (True, "plattegrond-bg-fouten.dxf")):
        doc = bouw(fouten)
        doc.saveas(HERE / naam)
        normaliseer(HERE / naam)

    pand = {
        "identificatie": PAND_ID, "bouwjaar": int(row["bouwjaar"]), "status": row["status"],
        "gebruiksdoel": row["gebruiksdoel"], "bag_oppervlakte_min": int(row["oppervlakte_min"]),
        "bag_oppervlakte_max": int(row["oppervlakte_max"]), "aantal_verblijfsobjecten": int(row["aantal_verblijfsobjecten"]),
        "oppervlakte_contour_m2": round(area(RD), 1), "crs": "EPSG:28992",
        "hoekpunten_rd": {k: list(v) for k, v in zip("ABCDEF", RD)},
        "bron": "BAG via PDOK, subset ~/django-lab/data/almere.gpkg (laag panden), gelezen 2026-10-24",
        "opmerking": "De plattegrond is fictief; alleen de contour is echt.",
    }
    (HERE / "pand.json").write_text(json.dumps(pand, indent=2, ensure_ascii=False) + "\n")

    pas = [{"naam": k, "lokaal_mm": list(L[k]), "rd_m": list(RD["ABCDEF".index(k)] if False else RD["ABCDEF".index(k)])} for k in "ABCF"]
    waarheid = {
        "beschrijving": "lokaal (mm, 1e kwadrant) -> RD (m): rd = B_rd + R(+theta) * (lokaal - (500,500)) / 1000",
        "schaal_lokaal_naar_rd": 0.001,
        "rotatie_lokaal_naar_rd_graden": round(math.degrees(TH), 6),
        "rotatie_rd_naar_lokaal_graden": round(math.degrees(ROT), 6),
        "oorsprong_lokaal_mm": [SHIFT, SHIFT], "oorsprong_lokaal_in_rd_m": list(B),
        "verschuiving_rd_m_van_lokaal_00": list(loc2rd((0, 0))),
        "affien_lokaal_mm_naar_rd_m": {
            "x_rd = a*x + b*y + c": [0.001 * math.cos(TH), -0.001 * math.sin(TH), loc2rd((0, 0))[0]],
            "y_rd = d*x + e*y + f": [0.001 * math.sin(TH), 0.001 * math.cos(TH), loc2rd((0, 0))[1]]},
        "paspunten": pas,
        "tolerantie": "lokale coordinaten zijn op 1 mm afgerond; terugrekenen geeft < 2 mm afwijking in RD",
        "crs_rd": "EPSG:28992",
    }
    (HERE / "georef-waarheid.json").write_text(json.dumps(waarheid, indent=2) + "\n")


def render():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from ezdxf.addons.drawing import Frontend, RenderContext
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    for naam, titel in (("plattegrond-bg", "render plattegrond-bg.dxf"), ("plattegrond-bg-fouten", "render plattegrond-bg-fouten.dxf (5 bewuste fouten)")):
        doc = ezdxf.readfile(HERE / f"{naam}.dxf")
        fig = plt.figure(figsize=(16, 16), dpi=100)
        ax = fig.add_axes([0.02, 0.02, 0.96, 0.93])
        ctx = RenderContext(doc)
        Frontend(ctx, MatplotlibBackend(ax)).draw_layout(doc.modelspace())
        ax.set_title(titel, fontsize=16)
        fig.set_size_inches(16, 16)
        fig.savefig(Path(tempfile.gettempdir()) / f"{naam}-render.png", dpi=150)
        plt.close(fig)


if __name__ == "__main__":
    schrijf()
    render()
    print("klaar")
