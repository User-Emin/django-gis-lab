from django.contrib.gis.db.models import PointField
from django.contrib.gis.db.models.functions import Centroid, Transform
from django.core.management.base import BaseCommand
from django.db.models.functions import Cast

from kaart.models import Pand


class Command(BaseCommand):
    help = "Vul Pand.midden_wgs (geometry 4326) en Pand.midden_geo (geography) uit de RD-geometrie."

    def handle(self, *args, **options):
        n = Pand.objects.update(midden_wgs=Transform(Centroid("geom"), 4326))
        Pand.objects.update(midden_geo=Cast("midden_wgs", PointField(geography=True)))
        self.stdout.write(f"Bijgewerkt: {n} panden")
