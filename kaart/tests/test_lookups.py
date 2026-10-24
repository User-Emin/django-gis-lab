import pytest
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.core.management import call_command

from kaart.models import Buurt, Pand

PUNT = Point(143515.95, 486811.47, srid=28992)


@pytest.fixture
def almere(db):
    call_command("laad_almere", verbosity=0)


def test_dwithin_rd_en_geography_geven_bijna_hetzelfde(almere):
    rd = Pand.objects.filter(geom__dwithin=(PUNT, D(m=250))).count()
    pt = PUNT.transform(4326, clone=True)
    geo = Pand.objects.filter(midden_geo__dwithin=(pt, D(m=250))).count()
    assert rd == 21  # afstand tot de rand van het pand
    assert geo == 16  # afstand tot het middelpunt, in meters


def test_dwithin_met_d_op_4326_geometry_faalt(almere):
    pt = PUNT.transform(4326, clone=True)
    with pytest.raises(ValueError, match="degree units"):
        Pand.objects.filter(midden_wgs__dwithin=(pt, D(m=250))).count()


def test_distance_sortering_nul_voor_pand_onder_punt(almere):
    eerste = Pand.objects.annotate(d=Distance("geom", PUNT)).order_by("d").first()
    assert eerste.d.m == 0


def test_buurt_bevat_punt(almere):
    assert Buurt.objects.get(geom__contains=PUNT).buurtnaam == "Centrum Stad Zuidoost"


def test_dichtstbij_vanaf_2000_gesorteerd(almere):
    from kaart.management.commands.dichtstbij import dichtstbij

    res = list(dichtstbij(PUNT, 2000, 10))
    assert len(res) == 10
    assert all(p.bouwjaar >= 2000 for p in res)
    afstanden = [p.d.m for p in res]
    assert afstanden == sorted(afstanden)
    assert afstanden[0] < 1  # het pand onder het punt (bouwjaar >= 2000 in de les)
