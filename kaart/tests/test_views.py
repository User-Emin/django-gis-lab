import pytest
from django.urls import reverse

from kaart.models import Project
from kaart.tests.factories import ProjectFactory, TekeningFactory

pytestmark = pytest.mark.django_db


def test_lijst_telt_tekeningen(client):
    p = ProjectFactory()
    TekeningFactory.create_batch(3, project=p)
    antwoord = client.get(reverse("kaart:project_lijst"))
    assert antwoord.status_code == 200
    assert antwoord.context["object_list"][0].aantal == 3


def test_lijst_gebruikt_vaste_aantal_queries(client, django_assert_num_queries):
    for p in ProjectFactory.create_batch(5):
        TekeningFactory.create_batch(2, project=p)
    with django_assert_num_queries(2):  # count voor paginering + de lijst zelf
        client.get(reverse("kaart:project_lijst"))


def test_detail_toont_tekeningen(client):
    t = TekeningFactory()
    antwoord = client.get(reverse("kaart:project_detail", args=[t.project.pk]))
    assert t.bestandsnaam in antwoord.content.decode()


def test_nieuw_project_opslaan(client):
    antwoord = client.post(
        reverse("kaart:project_nieuw"),
        {"naam": "Fietsbrug Noord", "opdrachtgever": "Almere", "status": "concept"},
    )
    assert antwoord.status_code == 302
    assert Project.objects.filter(naam="Fietsbrug Noord").exists()


def test_post_zonder_csrf_token_is_403(client):
    from django.test import Client

    strikt = Client(enforce_csrf_checks=True)
    antwoord = strikt.post(reverse("kaart:project_nieuw"), {"naam": "Zonder token"})
    assert antwoord.status_code == 403


def test_bewerken(client):
    p = ProjectFactory(naam="Oude naam")
    client.post(
        reverse("kaart:project_bewerk", args=[p.pk]),
        {"naam": "Nieuwe naam", "opdrachtgever": "Almere", "status": "afgerond"},
    )
    p.refresh_from_db()
    assert (p.naam, p.status) == ("Nieuwe naam", "afgerond")
