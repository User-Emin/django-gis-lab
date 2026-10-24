import factory

from kaart.models import Project, Tekening


class ProjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Project

    naam = factory.Sequence(lambda n: f"Testproject {n:03d}")
    opdrachtgever = "Gemeente Almere"
    status = Project.Status.CONCEPT


class TekeningFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tekening

    project = factory.SubFactory(ProjectFactory)
    naam = factory.Sequence(lambda n: f"Situatie {n}")
    bestandsnaam = factory.LazyAttribute(lambda o: f"{o.naam.lower().replace(' ', '-')}.dxf")
