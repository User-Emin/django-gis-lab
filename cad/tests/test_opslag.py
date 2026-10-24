import pytest
from django.core import signing
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage

from cad.models import Tekening
from cad.opslag import DjangoOpslag

pytestmark = pytest.mark.django_db


@pytest.fixture
def opslag(tmp_path):
    return DjangoOpslag(storage=FileSystemStorage(location=tmp_path, base_url="/m/"))


@pytest.fixture
def tekening():
    t = Tekening.objects.create(naam="t", eenheid="m", rapport={"oud": 1})
    t.bestand.save("t.dwg", ContentFile(b"DWG"), save=True)
    return t


def test_upload_dwg_geeft_ondertekende_get_url(opslag, tekening, settings):
    settings.CAD_PUBLIC_BASE_URL = "https://lab.example/"
    url = opslag.upload_dwg(tekening.pk)
    pad, token = url.split("?token=")
    assert pad == f"https://lab.example/m/{tekening.bestand.name}"
    assert opslag.controleer_token(token, "get") == tekening.bestand.name


def test_token_modus_en_vervalsing(opslag):
    _, token = opslag.schrijf_url("rcs/1.json").split("?token=")
    assert opslag.controleer_token(token, "put") == "pipeline/rcs/1.json"
    with pytest.raises(signing.BadSignature):
        opslag.controleer_token(token, "get")
    with pytest.raises(signing.BadSignature):
        opslag.controleer_token(token + "x", "put")


def test_token_verlopen(tmp_path, tekening):
    o = DjangoOpslag(storage=FileSystemStorage(location=tmp_path), geldig_s=-1)
    _, token = o.schrijf_url("a.json").split("?token=")
    with pytest.raises(signing.SignatureExpired):
        o.controleer_token(token, "put")


@pytest.mark.parametrize("key", ["../x", "a/../b", "/abs"])
def test_schrijf_url_weigert_pad_uitbraak(opslag, key):
    with pytest.raises(ValueError):
        opslag.schrijf_url(key)


def test_bewaar_status_behoudt_rapport_en_overschrijft(opslag, tekening):
    opslag.bewaar_status(tekening.pk, "wi9", "pending")
    opslag.bewaar_status(tekening.pk, "wi9", "success", "https://r/9")
    tekening.refresh_from_db()
    assert tekening.rapport["oud"] == 1
    assert tekening.rapport["rcs"] == {
        "workitem": "wi9",
        "status": "success",
        "reportUrl": "https://r/9",
    }


def test_bewaar_rapport_schrijft_in_storage_en_overschrijft(opslag):
    assert opslag.bewaar_rapport("rcs/1.json", b"a") == "pipeline/rcs/1.json"
    opslag.bewaar_rapport("rcs/1.json", b"bb")
    with opslag.storage.open("pipeline/rcs/1.json") as f:
        assert f.read() == b"bb"


def test_past_op_de_interface_van_voer_controle_uit(opslag, tekening):
    from rcs_tasks import voer_controle_uit

    class Client:
        def start_workitem(self, act, args):
            assert (
                args["inputFile"]["url"].startswith("/m/") or "?token=" in args["inputFile"]["url"]
            )
            return {"id": "w1", "status": "pending"}

        def wait_workitem(self, wid, timeout):
            return {"id": wid, "status": "success", "reportUrl": "https://r/1"}

    r = voer_controle_uit(tekening.pk, client=Client(), opslag=opslag, nickname="rvb")
    assert r["status"] == "success"
    tekening.refresh_from_db()
    assert tekening.rapport["rcs"]["status"] == "success"
