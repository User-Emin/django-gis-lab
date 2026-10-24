from io import StringIO

import pytest
from django.contrib.gis.geos import Point
from django.core.management import call_command

from kaart.models import Buurt, Pand


@pytest.fixture
def almere(db):
    call_command("laad_almere", stdout=StringIO())


def test_aantallen_uit_gpkg(almere):
    assert Buurt.objects.count() == 31
    assert Pand.objects.count() == 5726


def test_geometrie_in_rd_new_en_geldig(almere):
    pand = Pand.objects.first()
    assert pand.geom.srid == 28992
    assert pand.geom.geom_type == "MultiPolygon"
    assert not Pand.objects.exclude(geom__isvalid=True).exists()


def test_punt_in_centrum_ligt_in_een_buurt(almere):
    punt = Point(143550, 486850, srid=28992)
    assert Buurt.objects.filter(geom__contains=punt).count() == 1


@pytest.mark.django_db
def test_laad_almere_vanaf_bouwjaar():
    uit = StringIO()
    call_command("laad_almere", "--vanaf-bouwjaar=2000", stdout=uit)
    assert Pand.objects.count() > 0
    assert Pand.objects.count() < 5726
    assert not Pand.objects.filter(bouwjaar__lt=2000).exists()
    assert "Verwijderd (bouwjaar < 2000)" in uit.getvalue()
