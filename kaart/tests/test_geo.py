import pytest
from django.contrib.gis.geos import Point

from kaart.tests.factories import ProjectFactory

pytestmark = pytest.mark.django_db


def test_locatie_wordt_opgeslagen_in_rd_new():
    project = ProjectFactory(locatie=Point(143200, 486600, srid=28992))
    project.refresh_from_db()
    assert project.locatie.srid == 28992
    assert (project.locatie.x, project.locatie.y) == (143200, 486600)


def test_wgs84_invoer_wordt_automatisch_naar_rd_omgezet():
    """Een punt in lengte/breedte wordt bij opslaan naar het veld-SRID (28992) getransformeerd."""
    project = ProjectFactory(locatie=Point(5.2139522, 52.3671568, srid=4326))
    project.refresh_from_db()
    assert project.locatie.srid == 28992
    assert abs(project.locatie.x - 143200) < 1
    assert abs(project.locatie.y - 486600) < 1
