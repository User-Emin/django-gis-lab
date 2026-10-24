"""Les 08, Zelf: de ontbrekende regels uit het coverage-rapport afdekken."""

import pytest
from django.urls import reverse

from kaart.tests.factories import ProjectFactory, TekeningFactory

pytestmark = pytest.mark.django_db


def test_home_telt(client):
    TekeningFactory.create_batch(2)
    antwoord = client.get(reverse("kaart:home"))
    assert antwoord.context["aantal_tekeningen"] == 2
    assert antwoord.context["aantal_projecten"] == 2


def test_langzaam_doet_n_plus_1(client, django_assert_num_queries):
    TekeningFactory.create_batch(4)
    with django_assert_num_queries(1 + 4):
        client.get(reverse("kaart:tekeningen_langzaam"))


def test_snel_doet_een_query(client, django_assert_num_queries):
    TekeningFactory.create_batch(4)
    with django_assert_num_queries(1):
        client.get(reverse("kaart:tekeningen_snel"))


def test_str_van_project():
    assert str(ProjectFactory(naam="Fietsbrug")) == "Fietsbrug"


def test_projecten_overzicht_annotate(client, django_assert_num_queries):
    TekeningFactory.create_batch(3, project=ProjectFactory())
    with django_assert_num_queries(1):
        antwoord = client.get(reverse("kaart:projecten_overzicht"))
    assert antwoord.context["projecten"][0].aantal == 3
