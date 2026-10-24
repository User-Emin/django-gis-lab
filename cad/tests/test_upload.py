import json
from pathlib import Path

import ezdxf
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from cad.models import Ruimte, Tekening

DATA = Path(__file__).resolve().parents[2] / "data" / "cad"
pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def ingelogd(client, django_user_model):
    django_user_model.objects.create_user("tester", password="x")
    client.login(username="tester", password="x")
    return client


def _post(client, naam, inhoud, **extra):
    return client.post(
        reverse("cad:upload"), {"bestand": SimpleUploadedFile(naam, inhoud), **extra}
    )


def test_upload_zonder_login_gaat_naar_login(client):
    r = client.get(reverse("cad:upload"))
    assert r.status_code == 302
    assert r.url.startswith("/admin/login/")


def test_upload_goede_dxf_geeft_redirect_en_11_ruimtes(ingelogd):
    r = _post(ingelogd, "plattegrond-bg.dxf", (DATA / "plattegrond-bg.dxf").read_bytes())
    assert r.status_code == 302
    t = Tekening.objects.get()
    assert r.url == reverse("cad:tekening", args=[t.pk])
    assert Ruimte.objects.filter(tekening=t).count() == 11
    assert ingelogd.get(r.url).status_code == 200


def test_verkeerde_extensie_geeft_formulierfout(ingelogd):
    r = _post(ingelogd, "plan.txt", b"geen dxf")
    assert r.status_code == 200
    assert "Alleen .dxf" in r.context["form"].errors["bestand"][0]
    assert Tekening.objects.count() == 0


@override_settings(CAD_MAX_UPLOAD_BYTES=100)
def test_te_groot_geeft_formulierfout(ingelogd):
    r = _post(ingelogd, "groot.dxf", b"0" * 500)
    assert r.status_code == 200
    assert "maximum" in r.context["form"].errors["bestand"][0]


def test_zonder_insunits_wordt_geweigerd(ingelogd, tmp_path):
    doc = ezdxf.new("R2018")
    del doc.header["$INSUNITS"]
    pad = tmp_path / "zonder.dxf"
    doc.saveas(pad)
    r = _post(ingelogd, "zonder.dxf", pad.read_bytes())
    assert r.status_code == 200
    assert "$INSUNITS" in r.context["form"].errors["bestand"][0]
    assert Tekening.objects.count() == 0 and Ruimte.objects.count() == 0


def test_kapot_bestand_geeft_melding_geen_crash(ingelogd):
    r = _post(ingelogd, "kapot.dxf", b"dit is geen dxf\n" * 20)
    assert r.status_code == 200
    assert r.context["form"].errors["bestand"]
    assert Tekening.objects.count() == 0


def test_geojson_endpoint_geeft_11_features(ingelogd):
    _post(ingelogd, "plattegrond-bg.dxf", (DATA / "plattegrond-bg.dxf").read_bytes())
    t = Tekening.objects.get()
    r = ingelogd.get(reverse("cad:ruimtes", args=[t.pk]))
    data = json.loads(r.content)
    assert len(data["features"]) == 11 and len(data["bbox"]) == 4
    assert {"nummer", "ongeldig"} <= data["features"][0]["properties"].keys()


def test_geojson_zonder_login_redirect(client):
    assert client.get("/cad/api/tekening/1/ruimtes/").status_code == 302


def test_fouten_dxf_pagina_en_geojson_markeren_ongeldig(ingelogd):
    r = _post(ingelogd, "fouten.dxf", (DATA / "plattegrond-bg-fouten.dxf").read_bytes())
    pagina = ingelogd.get(r.url)
    assert pagina.status_code == 200
    assert "00.06" in pagina.content.decode()
    t = Tekening.objects.get()
    features = json.loads(ingelogd.get(reverse("cad:ruimtes", args=[t.pk])).content)["features"]
    assert [f["properties"]["nummer"] for f in features if f["properties"]["ongeldig"]] == ["00.06"]
