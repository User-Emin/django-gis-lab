from django.core.management.base import BaseCommand
from django.db import transaction

from kaart.laden import GPKG, buurt_mapping, laad, pand_mapping
from kaart.models import Buurt, Pand


class Command(BaseCommand):
    help = "Laad panden en buurten uit data/almere.gpkg (leegt eerst de tabellen)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--vanaf-bouwjaar",
            type=int,
            default=None,
            help="Bewaar alleen panden met bouwjaar >= dit jaar (Zelf-opdracht les 10).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        Pand.objects.all().delete()
        Buurt.objects.all().delete()
        laad(Buurt, buurt_mapping, "buurten")
        laad(Pand, pand_mapping, "panden")
        vanaf = options["vanaf_bouwjaar"]
        if vanaf is not None:
            # LayerMapping kan niet filteren: laden en daarna de oudere panden verwijderen.
            verwijderd, _ = Pand.objects.filter(bouwjaar__lt=vanaf).delete()
            self.stdout.write(f"Verwijderd (bouwjaar < {vanaf}): {verwijderd}")
        self.stdout.write(f"Bron: {GPKG.name}")
        self.stdout.write(f"Buurten: {Buurt.objects.count()}")
        self.stdout.write(f"Panden:  {Pand.objects.count()}")
