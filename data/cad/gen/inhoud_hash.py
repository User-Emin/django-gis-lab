#!/usr/bin/env python3
"""Inhoud-hash van een DXF: per entiteit dxftype, laag, coordinaten (0,01 mm), tekst en attribs, gesorteerd, sha256.
Bytes mogen verschillen (handles, tijdstempels); de inhoud niet. Gebruik: python inhoud_hash.py a.dxf [b.dxf ...]"""
import sys, hashlib, ezdxf

def r(v): return round(float(v) + 0.0, 2)

def punten(e):
    t = e.dxftype(); p = []
    if t in ("LINE",): p = [e.dxf.start, e.dxf.end]
    elif t == "LWPOLYLINE": p = [(x, y) for x, y, *_ in e.get_points()] + [("gesloten", e.closed)]
    elif t in ("TEXT",): p = [e.dxf.insert, e.dxf.get("align_point", (0, 0, 0))]
    elif t == "INSERT": p = [e.dxf.insert]
    elif t == "DIMENSION": p = [e.dxf.defpoint, e.dxf.defpoint2, e.dxf.defpoint3, e.dxf.text_midpoint]
    elif t == "HATCH":
        for path in e.paths:
            if hasattr(path, "vertices"): p += [tuple(v)[:2] for v in path.vertices]
            else: p += [(str(type(ed).__name__), *[r(x) for x in (getattr(ed, "start", (0, 0)) or (0, 0))]) for ed in path.edges]
    elif t in ("ARC", "CIRCLE"): p = [e.dxf.center, e.dxf.radius] + ([e.dxf.start_angle, e.dxf.end_angle] if t == "ARC" else [])
    out = []
    for q in p:
        if isinstance(q, (tuple, list)) or hasattr(q, "__iter__") and not isinstance(q, str):
            out.append(tuple(r(c) if isinstance(c, (int, float)) else str(c) for c in q))
        elif isinstance(q, (int, float)): out.append((r(q),))
        else: out.append((str(q),))
    return out

def regels(path):
    doc = ezdxf.readfile(path); res = []
    for e in doc.modelspace():
        t = e.dxftype()
        tekst = e.dxf.text if t == "TEXT" else ""
        att = sorted((a.dxf.tag, a.dxf.text) for a in e.attribs) if t == "INSERT" else []
        extra = e.dxf.name if t == "INSERT" else ""
        res.append(repr((t, e.dxf.layer, punten(e), tekst, att, extra)))
    return sorted(res)

def inhoud_hash(path):
    r_ = regels(path)
    return hashlib.sha256("\n".join(r_).encode()).hexdigest(), len(r_)

if __name__ == "__main__":
    for p in sys.argv[1:]:
        h, n = inhoud_hash(p); print(f"{h}  {n} entiteiten  {p}")
