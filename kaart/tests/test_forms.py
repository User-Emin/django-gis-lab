import pytest

from kaart.forms import ProjectForm
from kaart.tests.factories import ProjectFactory

pytestmark = pytest.mark.django_db


def test_geldig_formulier():
    form = ProjectForm(data={"naam": "Nieuwe wijk", "opdrachtgever": "Almere", "status": "concept"})
    assert form.is_valid(), form.errors


def test_te_korte_naam_wordt_geweigerd():
    form = ProjectForm(data={"naam": "Abc", "opdrachtgever": "Almere", "status": "concept"})
    assert not form.is_valid()
    assert "minstens 5 tekens" in form.errors["naam"][0]


def test_naam_is_niet_hoofdletterongevoelig_dubbel():
    """Nieuwe eis: 'Stadhuisplein' en 'stadhuisplein' zijn hetzelfde project."""
    ProjectFactory(naam="Stadhuisplein")
    form = ProjectForm(data={"naam": "stadhuisplein", "opdrachtgever": "A", "status": "concept"})
    assert not form.is_valid()
    assert "bestaat al" in form.errors["naam"][0]
