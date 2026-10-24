from django.contrib.gis.db.models.functions import Distance
from django.core.management.base import BaseCommand, CommandError

from kaart.models import Pand, Project


def dichtstbij(punt, vanaf_bouwjaar=2000, aantal=10):
    """Panden vanaf `vanaf_bouwjaar`, het dichtst bij `punt` (RD), met afstand `d` in meters."""
    return (
        Pand.objects.filter(bouwjaar__gte=vanaf_bouwjaar)
        .annotate(d=Distance("geom", punt))
        .order_by("d")[:aantal]
    )


class Command(BaseCommand):
    help = "Zelf les 11: de 10 panden (bouwjaar >= 2000) die het dichtst bij Project 1 liggen."

    def add_arguments(self, parser):
        parser.add_argument("--vanaf-bouwjaar", type=int, default=2000)
        parser.add_argument("--aantal", type=int, default=10)

    def handle(self, *args, **options):
        project = Project.objects.order_by("pk").first()
        if project is None or project.locatie is None:
            raise CommandError("Geen project met locatie; draai seed_demo en zet_demopunt.")
        self.stdout.write(f"{project.naam} op {project.locatie.coords}")
        for p in dichtstbij(project.locatie, options["vanaf_bouwjaar"], options["aantal"]):
            self.stdout.write(f"{p.d.m:8.1f} m  {p.identificatie}  bouwjaar {p.bouwjaar}")
