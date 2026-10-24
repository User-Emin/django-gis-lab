from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand, CommandError

from kaart.models import Pand, Project


class Command(BaseCommand):
    help = "Zet de locatie van het eerste project op de centroid van een echt BAG-pand."

    def handle(self, *args, **options):
        project = Project.objects.order_by("pk").first()
        if project is None:
            raise CommandError("Geen project; draai eerst seed_demo.")
        oud = project.locatie
        if oud is not None:
            naast = Pand.objects.annotate(d=Distance("geom", oud)).order_by("d").first()
            self.stdout.write(f"Oud punt {oud.coords}: dichtstbijzijnde pand op {naast.d.m:.0f} m")
        # pand dichtst bij het hart van Almere Stad (RD New)
        hart = Point(143550, 486850, srid=28992)
        pand = Pand.objects.annotate(d=Distance("geom", hart)).order_by("d").first()
        project.locatie = pand.geom.centroid
        project.save(update_fields=["locatie"])
        inpand = Pand.objects.filter(geom__contains=project.locatie).count()
        self.stdout.write(
            f"{project.naam}: nu op pand {pand.identificatie}, centroid {project.locatie.coords}"
        )
        self.stdout.write(
            f"Panden die het punt bevatten: {inpand} (centroid ligt niet altijd binnen het pand)"
        )
