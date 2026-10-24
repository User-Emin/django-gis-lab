from django.core.management.base import BaseCommand
from django.db import transaction

from kaart.laden import GPKG, buurt_mapping, laad, pand_mapping
from kaart.models import Buurt, Pand


class Command(BaseCommand):
    help = "Laad panden en buurten uit data/almere.gpkg (leegt eerst de tabellen)."

    @transaction.atomic
    def handle(self, *args, **options):
        Pand.objects.all().delete()
        Buurt.objects.all().delete()
        laad(Buurt, buurt_mapping, "buurten")
        laad(Pand, pand_mapping, "panden")
        self.stdout.write(f"Bron: {GPKG.name}")
        self.stdout.write(f"Buurten: {Buurt.objects.count()}")
        self.stdout.write(f"Panden:  {Pand.objects.count()}")
