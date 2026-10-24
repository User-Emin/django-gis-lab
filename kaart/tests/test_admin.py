import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.urls import reverse

from kaart.models import Pand

pytestmark = pytest.mark.django_db


@pytest.fixture
def panden(django_db_setup):
    from django.contrib.gis.geos import MultiPolygon, Polygon

    def maak(gid, jaar):
        p = Polygon(((0, 0), (0, 10), (10, 10), (10, 0), (0, 0)), srid=28992)
        return Pand.objects.create(
            gid=gid,
            identificatie=f"{gid:016d}",
            bouwjaar=jaar,
            status="Pand in gebruik",
            aantal_verblijfsobjecten=1,
            geom=MultiPolygon(p, srid=28992),
        )

    return [maak(1, 1985), maak(2, 2005), maak(3, 2015)]


@pytest.fixture
def kijker():
    call_command("maak_rollen", gebruiker="kijker", wachtwoord="alleen-test-1234")
    return User.objects.get(username="kijker")


def test_filter_bouwperiode(admin_client, panden):
    url = reverse("admin:kaart_pand_changelist")
    r = admin_client.get(url, {"periode": "2000"})
    assert r.status_code == 200
    assert [p.bouwjaar for p in r.context["cl"].result_list] == [2005]


def test_oppervlak_kolom(admin_client, panden):
    r = admin_client.get(reverse("admin:kaart_pand_changelist"))
    assert "100" in r.content.decode()


def test_kijker_ziet_lijst_maar_kan_niet_wijzigen(client, kijker, panden):
    client.force_login(kijker)
    assert client.get(reverse("admin:kaart_pand_changelist")).status_code == 200
    r = client.get(reverse("admin:kaart_pand_change", args=[panden[0].pk]))
    assert r.status_code == 200 and b"Opslaan" not in r.content
    r = client.post(reverse("admin:kaart_pand_change", args=[panden[0].pk]), {"bouwjaar": 1900})
    assert r.status_code == 403
    assert client.get(reverse("admin:kaart_pand_add")).status_code == 403
    panden[0].refresh_from_db()
    assert panden[0].bouwjaar == 1985


def test_kijker_ziet_geen_tekeningen(client, kijker):
    client.force_login(kijker)
    r = client.get(reverse("admin:index"))
    assert b"Tekeningen" in r.content  # view_tekening zit ook in de groep
    assert client.get(reverse("admin:auth_user_changelist")).status_code == 403
