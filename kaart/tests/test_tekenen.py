import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import GEOSGeometry
from django.template import Context, Template
from django.test import Client

from kaart.models import Project

pytestmark = pytest.mark.django_db

# Een vierkant van 100 m in Almere Centrum (RD New)
VLAK = {
    "type": "Polygon",
    "coordinates": [
        [[143500, 486800], [143600, 486800], [143600, 486900], [143500, 486900], [143500, 486800]]
    ],
}


@pytest.fixture
def manifest(tmp_path, settings):
    pad = tmp_path / "manifest.json"
    pad.write_text(
        json.dumps({"src/main.ts": {"file": "assets/main-abc.js", "css": ["assets/main-def.css"]}})
    )
    settings.VITE_MANIFEST = pad


@pytest.fixture
def project():
    return Project.objects.create(naam="Gebiedstest", opdrachtgever="Test")


@pytest.fixture
def browser(manifest):
    """Een client die CSRF echt afdwingt (de standaard testclient slaat die controle over)."""
    c = Client(enforce_csrf_checks=True)
    c.get("/kaart/")  # ensure_csrf_cookie zet de cookie csrftoken
    return c


def post(c, project, **extra):
    return c.post(
        "/api/gebieden/",
        data=json.dumps({"project": project.pk, "geometry": VLAK}),
        content_type="application/json",
        **extra,
    )


def inloggen(c):
    user = get_user_model().objects.create_user("tekenaar", password="x")
    c.force_login(user)


def test_post_met_login_en_csrf_slaat_op(browser, project):
    inloggen(browser)
    token = browser.cookies["csrftoken"].value
    r = post(browser, project, HTTP_X_CSRFTOKEN=token)
    assert r.status_code == 201
    project.refresh_from_db()
    assert project.gebied.srid == 28992
    assert project.gebied.area == pytest.approx(10000)
    assert r.json()["geometry"]["type"] == "Polygon"


def test_post_zonder_csrf_header_geeft_403(browser, project):
    inloggen(browser)
    r = post(browser, project)
    assert r.status_code == 403
    assert "CSRF" in r.json()["detail"]
    project.refresh_from_db()
    assert project.gebied is None


def test_post_met_csrf_maar_zonder_login_geeft_403(browser, project):
    r = post(browser, project, HTTP_X_CSRFTOKEN=browser.cookies["csrftoken"].value)
    assert r.status_code == 403


def test_ongeldig_vlak_geeft_400(browser, project):
    inloggen(browser)
    token = browser.cookies["csrftoken"].value
    bowtie = {
        "type": "Polygon",
        "coordinates": [[[0, 300000], [10, 300010], [10, 300000], [0, 300010], [0, 300000]]],
    }
    r = browser.post(
        "/api/gebieden/",
        data=json.dumps({"project": project.pk, "geometry": bowtie}),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert r.status_code == 400 and "Ongeldig" in json.dumps(r.json())


def test_gebieden_lezen_zonder_login_kan(client, project):
    project.gebied = GEOSGeometry(json.dumps(VLAK))
    project.gebied.srid = 28992
    project.save()
    d = client.get("/api/gebieden/?srid=28992").json()
    assert d["count"] == 1
    assert d["features"][0]["geometry"]["coordinates"][0][0] == [143500.0, 486800.0]


def test_bestaande_projecten_blijven_alleen_lezen(browser, project):
    inloggen(browser)
    r = browser.post(
        "/api/projecten/",
        data="{}",
        content_type="application/json",
        HTTP_X_CSRFTOKEN=browser.cookies["csrftoken"].value,
    )
    assert r.status_code == 405
    assert browser.get("/api/projecten/").status_code == 200


def test_kaartpagina_laadt_gehashte_bestanden_uit_manifest(client, manifest):
    html = client.get("/kaart/").content.decode()
    assert "/static/app/assets/main-abc.js" in html
    assert "/static/app/assets/main-def.css" in html
    assert "csrftoken" in client.cookies


def test_tag_zonder_build_geeft_duidelijke_fout(settings, tmp_path):
    settings.VITE_MANIFEST = tmp_path / "bestaat-niet.json"
    from django.template import TemplateSyntaxError

    with pytest.raises(TemplateSyntaxError, match="npm run build"):
        Template('{% load vite %}{% vite_js "src/main.ts" %}').render(Context())


def test_vlak_buiten_almere_geeft_400(browser, project):
    """Zelf 15: een geldig RD-vlak in Amsterdam (x 121000, y 487000) wordt geweigerd."""
    inloggen(browser)
    amsterdam = {
        "type": "Polygon",
        "coordinates": [
            [
                [121000, 487000],
                [121100, 487000],
                [121100, 487100],
                [121000, 487100],
                [121000, 487000],
            ]
        ],
    }
    r = browser.post(
        "/api/gebieden/",
        data=json.dumps({"project": project.pk, "geometry": amsterdam}),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=browser.cookies["csrftoken"].value,
    )
    assert r.status_code == 400
    assert "buiten Almere" in json.dumps(r.json())
    project.refresh_from_db()
    assert project.gebied is None
