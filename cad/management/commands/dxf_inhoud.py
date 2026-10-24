"""python manage.py dxf_inhoud data/cad/plattegrond-bg.dxf

Print wat er in een DXF staat, in de volgorde van het bestand: HEADER, TABLES, BLOCKS, ENTITIES.
"""

from pathlib import Path

import ezdxf
from django.core.management.base import BaseCommand, CommandError
from ezdxf import DXFError

from cad import dxf


class Command(BaseCommand):
    help = "Toon HEADER, lagen, blocks en entiteiten van een DXF-bestand."

    def add_arguments(self, parser):
        parser.add_argument("bestand", type=Path)

    def handle(self, *args, bestand: Path, **opties):
        try:
            doc = ezdxf.readfile(bestand)
        except (OSError, DXFError) as fout:
            raise CommandError(f"Kan {bestand} niet lezen: {fout}") from fout
        msp = doc.modelspace()
        out = self.stdout.write

        out(f"== HEADER ({bestand.name}, ezdxf {ezdxf.__version__})")
        for naam, waarde in dxf.header_variabelen(doc).items():
            out(f"{naam:13} {waarde}")
        if dxf.header_variabelen(doc)["$EXTMIN"][0] > 1e19:
            lo, hi = dxf.extents(doc)
            out(f"(EXTMIN/EXTMAX staan op 1e+20 = niet berekend; gemeten: {lo[:2]} .. {hi[:2]})")
        out(f"1 unit = 1 {dxf.eenheid_naam(doc)}  (= {dxf.meter_per_unit(doc)} m)")

        out("\n== TABLES: lagen")
        out(f"{'laag':28} {'kleur':>5} {'linetype':11} {'aan':>5} {'bevroren':>8}")
        for laag in dxf.lagen(doc):
            out(
                f"{laag['naam']:28} {laag['kleur']:>5} {laag['linetype']:11} "
                f"{laag['aan']!s:>5} {laag['bevroren']!s:>8}"
            )

        out("\n== BLOCKS")
        for naam, attdefs in dxf.blocks(doc).items():
            out(f"{naam}  ATTDEF: {', '.join(attdefs) or '-'}")

        out("\n== ENTITIES: aantal per (type, laag)")
        telling = dxf.tel_entiteiten(msp)
        for (soort, laag), n in sorted(telling.items()):
            out(f"{n:4}  {soort:10} {laag}")
        out(f"{sum(telling.values()):4}  totaal")

        out("\n== Per type een voorbeeld")
        self._voorbeelden(msp)

    def _voorbeelden(self, msp):
        out = self.stdout.write
        boog = next(
            (e for e in msp.query("LWPOLYLINE") if any(b for *_, b in dxf.polylijn_punten(e))),
            None,
        )
        if boog:
            punten = dxf.polylijn_punten(boog)
            out(f"LWPOLYLINE met bulge (laag {boog.dxf.layer}), is_closed={boog.is_closed}")
            for x, y, b in punten:
                out(f"  punt ({x:.1f}, {y:.1f})  bulge {b:+.4f}")
            (x1, y1, b), (x2, y2, _) = punten[0], punten[1]
            out(f"  segment 1 is een boog: {dxf.bulge_naar_boog((x1, y1), (x2, y2), b)}")
        if arc := next(iter(msp.query("ARC")), None):
            d = arc.dxf
            out(
                f"ARC center=({d.center.x:.1f}, {d.center.y:.1f}) radius={d.radius:.1f} "
                f"van {d.start_angle:.0f} tot {d.end_angle:.0f} graden (tegen de klok in)"
            )
        if ins := next(iter(msp.query("INSERT")), None):
            attribs = {a.dxf.tag: a.dxf.text for a in ins.attribs}
            out(
                f"INSERT block={ins.dxf.name} insert=({ins.dxf.insert.x:.1f}, "
                f"{ins.dxf.insert.y:.1f}) rotatie={ins.dxf.rotation:.0f} attribs={attribs}"
            )
        if txt := next(iter(msp.query("TEXT")), None):
            d = txt.dxf
            out(
                f"TEXT {d.text!r} insert=({d.insert.x:.1f}, {d.insert.y:.1f}) "
                f"hoogte={d.height:.0f} laag={d.layer}"
            )
