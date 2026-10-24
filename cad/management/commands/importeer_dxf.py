"""python manage.py importeer_dxf <pad> [--pand BAG-id]

Importeert de ruimtes uit een DXF en print het rapport.
"""

import json
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from cad.importeren import ImportFout, importeer_dxf
from cad.models import Tekening


class Command(BaseCommand):
    help = "Importeer de ruimtes (laag '92 ...') uit een DXF en print het rapport."

    def add_arguments(self, parser):
        parser.add_argument("pad", type=Path)
        parser.add_argument("--pand", default="", help="BAG-pand-id (anders uit de tekening)")
        parser.add_argument("--boog-tolerantie", type=float, default=0.001, help="meter")
        parser.add_argument("--sluit-tolerantie", type=float, default=0.05, help="meter")

    def handle(self, *args, pad: Path, pand, boog_tolerantie, sluit_tolerantie, **opties):
        if not pad.is_file():
            raise CommandError(f"{pad} bestaat niet")
        tekening = Tekening(naam=pad.name, bag_pand_id=pand)
        with pad.open("rb") as f:
            tekening.bestand.save(pad.name, File(f), save=False)
        tekening.eenheid = "?"
        tekening.save()
        try:
            rapport = importeer_dxf(pad, tekening, boog_tolerantie, sluit_tolerantie)
        except ImportFout as fout:
            tekening.delete()
            raise CommandError(str(fout)) from fout
        self.stdout.write(f"Tekening {tekening.pk}: {tekening.naam} (pand {tekening.bag_pand_id})")
        self.stdout.write(json.dumps(rapport, indent=2, ensure_ascii=False))
