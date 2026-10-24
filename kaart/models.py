from django.contrib.gis.db import models


class Project(models.Model):
    class Status(models.TextChoices):
        CONCEPT = "concept", "Concept"
        UITVOERING = "uitvoering", "In uitvoering"
        AFGEROND = "afgerond", "Afgerond"

    naam = models.CharField(max_length=120, unique=True)
    opdrachtgever = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=Status, default=Status.CONCEPT)
    aangemaakt = models.DateTimeField(auto_now_add=True)
    # RD New (EPSG:28992): x/y in meters, zie les 02
    locatie = models.PointField(srid=28992, null=True, blank=True)
    gebied = models.PolygonField(srid=28992, null=True, blank=True)

    class Meta:
        ordering = ["naam"]

    def __str__(self) -> str:
        return self.naam


class Tekening(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tekeningen")
    naam = models.CharField(max_length=120)
    bestandsnaam = models.CharField(max_length=200)
    versie = models.PositiveSmallIntegerField(default=1)
    geupload_op = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["project_id", "naam"]
        verbose_name_plural = "tekeningen"
        constraints = [
            models.UniqueConstraint(
                fields=["project", "naam", "versie"], name="uniek_tekening_versie"
            )
        ]

    def __str__(self) -> str:
        return f"{self.naam} v{self.versie}"
