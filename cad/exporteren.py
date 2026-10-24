"""Terug naar CAD: ruimtes uit PostGIS naar een DXF, per laag, met RCS-laagnamen.

Keuzes (les 20)
---------------
* **DXF-versie R2018 (AC1032)**: dezelfde versie als de plattegronden die we importeren
  (``plattegrond-bg.dxf`` is AC1032). Een export in een andere versie verandert dus niets aan de
  rondreis. R2013 (AC1027) zou ook openen in AutoCAD 2013-2017; welke AutoCAD-versie het RVB
  gebruikt is niet bekend (zie feiten) en dus een open punt.
* **Eenheden**: ``$INSUNITS`` 4 (mm) bij ``crs="lokaal"``, 6 (m) bij ``crs="rd"``. De codes
  komen uit ``ezdxf.units`` (MM = 4, M = 6; de DXF Reference kent dezelfde tabel). RCS §1.5.1:
  in een layout tab geldt 1 unit = 1 mm; een RD-tekening in meters is dus een afwijking die bij
  het opleveren aan de RCS moet worden getoetst.
* **Lokaal** = inverse van de affiene matrix uit ``Tekening.georef``: RD (m) -> lokaal (m) -> mm.
* **Lagen**: ``92 Rust- en werkgebieden`` (gesloten LWPOLYLINE per ruimte, plus het label als
  block ``RUIMTELABEL`` met ATTRIB RUIMTENR/FUNCTIE: de importer en ``dxf_inhoud`` begrijpen dat,
  en een ATTRIB is bevraagbare data, TEXT niet). ``99 Tekst`` = titelregel. Laag ``0`` blijft leeg
  (RCS §1.4). Lagen worden alleen aangemaakt als ze iets bevatten (RCS: geen lege lagen).
* Eigen keuzes, niet uit een norm (⚠️): ``00 BAG-pand`` (contour van het BAG-pand) en
  ``00 Controle`` (foutvlakken, rood). Een NL/SfB-code voor "BAG-pand" is niet nagezocht; ``00``
  is hier alleen "buiten de bouwkundige elementen". RCS-syntax is wel gevolgd: twee cijfers,
  spatie, omschrijving, alleen ``-`` en ``_`` als bijzonder teken.
"""

from math import hypot

import ezdxf
from django.contrib.gis.geos import GEOSGeometry
from ezdxf import units
from ezdxf.document import Drawing

from cad import kwaliteit
from cad.dxf import LABELBLOCK, RUIMTELAAG
from cad.models import Tekening
from kaart.models import Pand

VERSIE = "R2018"
LAAG_PAND = "00 BAG-pand"
LAAG_CONTROLE = "00 Controle"
LAAG_TEKST = "99 Tekst"
INSUNITS = {"lokaal": units.MM, "rd": units.M}
ROOD = 1


class ExportFout(Exception):
    pass


def inverse(matrix) -> tuple[float, ...]:
    """Inverse van x' = a x + b y + c, y' = d x + e y + f."""
    a, b, c, d, e, f = matrix
    det = a * e - b * d
    if abs(det) < 1e-12:
        raise ExportFout("singuliere transformatie")
    ia, ib, id_, ie = e / det, -b / det, -d / det, a / det
    return ia, ib, -(ia * c + ib * f), id_, ie, -(id_ * c + ie * f)


class Stelsel:
    """Zet RD-coordinaten om naar de tekeneenheden van het gekozen stelsel."""

    def __init__(self, tekening: Tekening, crs: str):
        if crs not in INSUNITS:
            raise ExportFout(f"crs moet 'rd' of 'lokaal' zijn, niet {crs!r}")
        self.crs = crs
        self.inv = None
        if crs == "lokaal":
            m = tekening.georef.get("matrix")
            if not m:
                raise ExportFout("tekening heeft geen georef.matrix: eerst `georefereer`")
            self.inv = inverse(m)
        self.hoogte = 1.0 if crs == "rd" else 1000.0  # m -> tekeneenheid

    def punt(self, x: float, y: float) -> tuple[float, float]:
        if self.inv is None:
            return (x, y)
        a, b, c, d, e, f = self.inv
        return ((a * x + b * y + c) * 1000.0, (d * x + e * y + f) * 1000.0)

    def ring(self, ring) -> list[tuple[float, float]]:
        pts = [self.punt(x, y) for x, y in ring.coords]
        return pts[:-1]  # laatste = eerste; de polylijn is gesloten


def _polygonen(geom):
    """Alle Polygon-delen van een (Multi)Polygon of GeometryCollection."""
    if geom.geom_type == "Polygon":
        yield geom
    elif hasattr(geom, "__iter__"):
        for deel in geom:
            yield from _polygonen(deel)


def _laag(doc: Drawing, naam: str, kleur: int) -> str:
    if naam not in doc.layers:
        doc.layers.add(naam, color=kleur)
    return naam


def exporteer(tekening: Tekening, crs: str = "rd", pand_id: str = "") -> tuple[Drawing, dict]:
    """Bouw het DXF-document; geef (doc, rapport)."""
    st = Stelsel(tekening, crs)
    ruimtes = list(tekening.ruimtes.exclude(geom_rd__isnull=True))
    if not ruimtes:
        raise ExportFout("geen geom_rd: eerst `georefereer` draaien")
    doc = ezdxf.new(VERSIE, setup=False)
    doc.header["$INSUNITS"] = INSUNITS[crs]
    doc.header["$LUNITS"] = 2  # decimaal (RCS: LUNITS=2)
    doc.header["$MEASUREMENT"] = 1  # metrisch
    msp = doc.modelspace()
    h = st.hoogte
    rapport = {"crs": crs, "versie": VERSIE, "insunits": INSUNITS[crs], "ruimtes": 0}

    blk = doc.blocks.new(LABELBLOCK)
    blk.add_attdef("RUIMTENR", (0, 0), text="00.00", dxfattribs={"height": 0.35 * h})
    blk.add_attdef("FUNCTIE", (0, -0.5 * h), text="functie", dxfattribs={"height": 0.25 * h})

    laag92 = _laag(doc, RUIMTELAAG, 5)
    for r in ruimtes:
        pts = st.ring(r.geom_rd[0])
        msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": laag92})
        c = r.geom_rd.point_on_surface
        x, y = st.punt(c.x, c.y)
        ins = msp.add_blockref(LABELBLOCK, (x, y), dxfattribs={"layer": laag92})
        ins.add_attrib(
            "RUIMTENR", r.nummer, (x, y), dxfattribs={"height": 0.35 * h, "layer": laag92}
        )
        ins.add_attrib(
            "FUNCTIE", r.naam, (x, y - 0.5 * h), dxfattribs={"height": 0.25 * h, "layer": laag92}
        )
        rapport["ruimtes"] += 1

    pand = Pand.objects.filter(identificatie=pand_id or tekening.bag_pand_id).first()
    if pand is not None:
        laag = _laag(doc, LAAG_PAND, 3)
        for mp in _polygonen(pand.geom):
            msp.add_lwpolyline(st.ring(mp[0]), close=True, dxfattribs={"layer": laag})
        rapport["pand"] = pand.identificatie

    fouten = {"ongeldig": [], "overlap": []}
    for g in kwaliteit.geldigheid(tekening.pk):
        if not g["geldig"]:
            r = next(r for r in ruimtes if r.pk == g["id"])
            laag = _laag(doc, LAAG_CONTROLE, ROOD)
            msp.add_lwpolyline(
                st.ring(r.geom_rd[0]), close=True, dxfattribs={"layer": laag, "color": ROOD}
            )
            c = r.geom_rd.envelope.centroid
            x, y = st.punt(c.x, c.y)
            msp.add_text(
                f"ONGELDIG {g['nummer']}: {g['reden'].split('[')[0]}",
                height=0.3 * h,
                dxfattribs={"layer": laag, "color": ROOD, "insert": (x, y)},
            )
            fouten["ongeldig"].append(g["nummer"])
    for o in kwaliteit.overlap_geometrie(tekening.pk):
        laag = _laag(doc, LAAG_CONTROLE, ROOD)
        geom = GEOSGeometry(o["geojson"], srid=28992)
        for poly in _polygonen(geom):
            msp.add_lwpolyline(
                st.ring(poly[0]), close=True, dxfattribs={"layer": laag, "color": ROOD}
            )
        c = geom.centroid
        x, y = st.punt(c.x, c.y)
        msp.add_text(
            f"OVERLAP {o['a']}/{o['b']} {o['oppervlakte']:.2f} m2",
            height=0.3 * h,
            dxfattribs={"layer": laag, "color": ROOD, "insert": (x, y)},
        )
        fouten["overlap"].append([o["a"], o["b"], round(o["oppervlakte"], 3)])
    rapport["fouten"] = fouten

    laag = _laag(doc, LAAG_TEKST, 7)
    ll = st.punt(*tekening.ruimtes.first().geom_rd.extent[:2])
    msp.add_text(
        f"{tekening.naam} ({crs}, export uit PostGIS)",
        height=0.5 * h,
        dxfattribs={"layer": laag, "insert": (ll[0], ll[1] - 3 * h)},
    )

    if "Defpoints" in doc.layers and not any(e.dxf.layer == "Defpoints" for e in msp):
        doc.layers.remove("Defpoints")
    from ezdxf import bbox

    ext = bbox.extents(msp)
    doc.header["$EXTMIN"] = tuple(ext.extmin)
    doc.header["$EXTMAX"] = tuple(ext.extmax)
    return doc, rapport


def rondreis(tekening: Tekening, doc: Drawing, crs: str, origineel=None) -> dict:
    """Vergelijk de geexporteerde ruimte-vertices met de bron, in mm (lokaal) of m (rd).

    1. met ``Ruimte.geom`` (de lokale meters uit de import) x 1000: elke ruimte, vertex voor vertex;
    2. met de oorspronkelijke DXF (``origineel``, ezdxf-doc in mm): per ruimte de polylijn met
       hetzelfde aantal punten en het dichtstbijzijnde middelpunt.
    """
    uit = [
        [(p[0], p[1]) for p in pl.get_points("xy")]
        for pl in doc.modelspace().query(f'LWPOLYLINE[layer=="{RUIMTELAAG}"]')
    ]
    ruimtes = list(tekening.ruimtes.exclude(geom_rd__isnull=True))
    res = {"crs": crs, "n": len(uit), "eenheid": "mm" if crs == "lokaal" else "m"}
    if crs != "lokaal":
        res["let_op"] = "rd: vergelijking met geom_rd (m), geen lokaal"
    afw = []
    for r, pts in zip(ruimtes, uit, strict=True):
        if crs == "lokaal":
            bron = [(x * 1000, y * 1000) for x, y in r.geom.coords[0][:-1]]
        else:
            bron = list(r.geom_rd.coords[0][:-1])
        afw.append(max(hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(pts, bron, strict=True)))
    res["max_afwijking_vs_db"] = max(afw)
    res["afwijking_per_ruimte"] = dict(zip((r.nummer for r in ruimtes), afw, strict=True))
    if origineel is not None and crs == "lokaal":
        orig = [
            [(p[0], p[1]) for p in pl.get_points("xy")]
            for pl in origineel.modelspace().query(f'LWPOLYLINE[layer=="{RUIMTELAAG}"]')
        ]
        mx, gevonden = 0.0, 0
        for pts in uit:
            kand = [o for o in orig if len(o) == len(pts)]
            if not kand:
                continue
            cx = sum(p[0] for p in pts) / len(pts)
            cy = sum(p[1] for p in pts) / len(pts)
            o = min(
                kand,
                key=lambda o: hypot(
                    sum(p[0] for p in o) / len(o) - cx, sum(p[1] for p in o) / len(o) - cy
                ),
            )
            # startpunt kan verschillen na ST_/GEOS: kies de beste cyclische verschuiving
            beste = min(
                max(
                    hypot(
                        pts[(i + k) % len(pts)][0] - o[i][0], pts[(i + k) % len(pts)][1] - o[i][1]
                    )
                    for i in range(len(o))
                )
                for k in range(len(o))
            )
            mx = max(mx, beste)
            gevonden += 1
        res["max_afwijking_vs_origineel_dxf"] = mx
        res["ruimtes_gekoppeld_aan_origineel"] = gevonden
    return res
