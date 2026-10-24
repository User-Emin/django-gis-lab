import random

from django.core.management.base import BaseCommand
from django.db import transaction

from kaart.models import Project, Tekening

STRAATEN = [
    "Stadhuisplein",
    "Weteringpark",
    "Kruidenwijk",
    "Hoge Vaart",
    "Noorderplassen",
    "Poort",
    "Filmwijk",
]
SOORTEN = ["Herinrichting", "Rioolvervanging", "Groenstrook", "Fietspad", "Speelplek"]


class Command(BaseCommand):
    help = "Maak demo-projecten met tekeningen (idempotent per naam)."

    def add_arguments(self, parser):
        parser.add_argument("--projecten", type=int, default=25)

    @transaction.atomic
    def handle(self, *args, projecten, **options):
        rng = random.Random(42)
        nieuw = 0
        for i in range(projecten):
            naam = f"{SOORTEN[i % len(SOORTEN)]} {STRAATEN[i % len(STRAATEN)]} {i + 1}"
            project, gemaakt = Project.objects.get_or_create(
                naam=naam,
                defaults={
                    "opdrachtgever": "Gemeente Almere",
                    "status": rng.choice(Project.Status.values),
                },
            )
            if gemaakt:
                nieuw += 1
                for j in range(rng.randint(2, 5)):
                    Tekening.objects.create(
                        project=project,
                        naam=f"Situatie {j + 1}",
                        bestandsnaam=f"p{i + 1:02d}-sit{j + 1}.dxf",
                    )
        self.stdout.write(
            self.style.SUCCESS(
                f"{nieuw} nieuwe projecten, {Tekening.objects.count()} tekeningen totaal"
            )
        )
