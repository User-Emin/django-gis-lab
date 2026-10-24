"""python manage.py controleer_tekening <id> [--pand BAGID] [--drempel M2] [--explain]

Controleert een georefereerde tekening: geldigheid (ST_IsValid, MakeValid als voorstel),
overlap tussen ruimtes en het verschil met het BAG-pand. Slaat niets op.
"""

from django.core.management.base import BaseCommand, CommandError

from cad import kwaliteit
from cad.models import Tekening


class Command(BaseCommand):
    help = "Controleer geldigheid, overlap en ligging t.o.v. het BAG-pand (geom_rd)."

    def add_arguments(self, parser):
        parser.add_argument("tekening_id", type=int)
        parser.add_argument(
            "--pand", default="", help="BAG-pand-id (standaard: tekening of lab-pand)"
        )
        parser.add_argument("--drempel", type=float, default=kwaliteit.DREMPEL_M2)
        parser.add_argument(
            "--explain", action="store_true", help="toon EXPLAIN van de overlap-query"
        )

    def handle(self, *args, tekening_id, pand, drempel, explain, **opties):
        try:
            t = Tekening.objects.get(pk=tekening_id)
        except Tekening.DoesNotExist:
            raise CommandError(f"tekening {tekening_id} bestaat niet") from None
        if not t.ruimtes.filter(geom_rd__isnull=False).exists():
            raise CommandError("geen geom_rd: eerst `georefereer` draaien")
        pand = pand or t.bag_pand_id or kwaliteit.STANDAARD_PAND
        w = self.stdout.write
        w(f"Tekening {t.pk} ({t.naam}), pand {pand}, overlapdrempel {drempel} m2")

        g = kwaliteit.geldigheid(t.pk)
        ongeldig = [r for r in g if not r["geldig"]]
        w(f"\n1. Geldigheid: {len(g)} ruimtes, {len(ongeldig)} ongeldig")
        for r in ongeldig:
            w(f"  {r['nummer'] or '?'}: {r['reden']}")
            w(
                f"    oppervlakte voor MakeValid {r['oppervlakte_voor']:.4f} m2, "
                f"na {r['oppervlakte_na']:.4f} m2 ({r['type_na']})"
            )
            w("    voorstel, NIET opgeslagen: MakeValid raadt de bedoeling; de tekenaar beslist.")

        o = kwaliteit.overlap(t.pk, drempel)
        w(f"\n2. Overlap (> {drempel} m2, aanraken telt niet): {len(o)} paar(en)")
        for r in o:
            w(f"  {r['a']} / {r['b']}: {r['oppervlakte']:.2f} m2")

        try:
            p = kwaliteit.pandverschil(t.pk, pand)
        except ValueError as fout:
            raise CommandError(str(fout)) from fout
        w(f"\n3. Plattegrond minus pand {p['pand_id']}")
        w(f"  unie ruimtes {p['plattegrond_m2']:.2f} m2, pand {p['pand_m2']:.2f} m2")
        w(f"  buiten het pand: {p['buiten_m2']:.2f} m2")
        w(f"  pand zonder ruimte: {p['onbedekt_m2']:.2f} m2")
        w(f"  pand gedekt: {p['dekking_pct']:.1f} %")

        if explain:
            w("\nEXPLAIN ANALYZE overlap-query (planner kiest zelf):")
            w(kwaliteit.explain_overlap(t.pk, drempel))
            w("\nzelfde, met enable_seqscan = off (alleen deze transactie):")
            w(kwaliteit.explain_overlap(t.pk, drempel, zonder_seqscan=True))
