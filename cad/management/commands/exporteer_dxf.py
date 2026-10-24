"""python manage.py exporteer_dxf <tekening_id> <uit.dxf> [--crs rd|lokaal] [--origineel in.dxf]

Schrijft de ruimtes van een gegeorefereerde tekening als DXF (R2018) met RCS-laagnamen.
Met ``--crs lokaal`` gaat het via de inverse van de affiene matrix terug naar mm; dan wordt ook
de rondreis gemeten (export tegenover de database en, met ``--origineel``, de oorspronkelijke DXF).
"""

import logging
from pathlib import Path

import ezdxf
from django.core.management.base import BaseCommand, CommandError

from cad import exporteren
from cad.models import Tekening


class Command(BaseCommand):
    help = "Exporteer een tekening uit PostGIS naar DXF."

    def add_arguments(self, parser):
        parser.add_argument("tekening_id", type=int)
        parser.add_argument("uit", type=Path)
        parser.add_argument("--crs", choices=["rd", "lokaal"], default="rd")
        parser.add_argument(
            "--zonder-controle", action="store_true", help='laat laag "00 Controle" weg'
        )
        parser.add_argument("--origineel", type=Path, help="oorspronkelijke DXF voor de rondreis")

    def handle(self, *args, tekening_id, uit, crs, origineel, zonder_controle, **opties):
        try:
            t = Tekening.objects.get(pk=tekening_id)
        except Tekening.DoesNotExist:
            raise CommandError(f"tekening {tekening_id} bestaat niet") from None
        logging.getLogger("ezdxf").setLevel(logging.WARNING)
        w = self.stdout.write
        try:
            doc, rapport = exporteren.exporteer(t, crs, controle=not zonder_controle)
        except exporteren.ExportFout as fout:
            raise CommandError(str(fout)) from fout
        doc.saveas(uit)
        w(f"Tekening {t.pk} ({t.naam}) -> {uit}")
        w(f"versie {rapport['versie']}, crs {crs}, $INSUNITS {rapport['insunits']}")
        w(f"ruimtes: {rapport['ruimtes']}, pand: {rapport.get('pand', '-')}")
        f = rapport["fouten"]
        w(f"fouten: ongeldig {f['ongeldig']}, overlap {f['overlap']}")
        if crs == "lokaal":
            orig = ezdxf.readfile(origineel) if origineel else None
            r = exporteren.rondreis(t, ezdxf.readfile(uit), crs, orig)
            w(f"rondreis max afwijking vs database: {r['max_afwijking_vs_db']:.3e} mm")
            if orig is not None:
                w(
                    "rondreis max afwijking vs oorspronkelijke DXF: "
                    f"{r['max_afwijking_vs_origineel_dxf']:.3e} mm "
                    f"({r['ruimtes_gekoppeld_aan_origineel']} ruimtes gekoppeld)"
                )
