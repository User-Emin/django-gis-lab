"""Opslag voor de AutoCAD-pipeline (les 22): ``DjangoOpslag``.

Interface (zoals ``pipeline/django-integratie/rcs_tasks.py`` ``voer_controle_uit`` die gebruikt):

* ``upload_dwg(tekening_id)``  -> URL waarmee de worker/DA de tekening kan LEZEN
* ``schrijf_url(key)``         -> URL waarmee DA een uitvoerbestand kan SCHRIJVEN (``put``)
* ``bewaar_status(tekening_id, workitem_id, status, report_url=None)`` -> status vastleggen

Bestanden staan in ``default_storage`` (``FileSystemStorage`` in ``MEDIA_ROOT``). De URL's
zijn ondertekend met ``django.core.signing`` (verloopt na ``geldig_s``, standaard 1 uur) en
absoluut als ``CAD_PUBLIC_BASE_URL`` gezet is. ⚠️ Deze klasse maakt alleen de URL's; een view die
het token controleert en een PUT accepteert is niet gebouwd. Echte S3-achtige pre-signed URL's
(zoals in prod nodig, want DA bereikt localhost niet) vragen een andere storage-backend.
"""

from __future__ import annotations

from django.conf import settings
from django.core import signing
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from .models import Tekening

SALT = "cad.opslag"
RAPPORT_SLEUTEL = "rcs"


class DjangoOpslag:
    def __init__(self, storage=None, geldig_s: int = 3600):
        self.storage = storage or default_storage
        self.geldig_s = geldig_s

    def _url(self, naam: str, modus: str) -> str:
        token = signing.dumps({"naam": naam, "modus": modus}, salt=SALT)
        basis = getattr(settings, "CAD_PUBLIC_BASE_URL", "").rstrip("/")
        return f"{basis}{self.storage.url(naam)}?token={token}"

    def controleer_token(self, token: str, modus: str) -> str:
        """Geeft de bestandsnaam terug of gooit ``signing.BadSignature``/``SignatureExpired``."""
        data = signing.loads(token, salt=SALT, max_age=self.geldig_s)
        if data["modus"] != modus:
            raise signing.BadSignature("verkeerde modus")
        return data["naam"]

    def upload_dwg(self, tekening_id: int) -> str:
        tekening = Tekening.objects.get(pk=tekening_id)
        return self._url(tekening.bestand.name, "get")

    def schrijf_url(self, key: str) -> str:
        if ".." in key.split("/") or key.startswith("/"):
            raise ValueError(f"ongeldige sleutel: {key!r}")
        naam = f"pipeline/{key}"
        return self._url(naam, "put")

    def bewaar_rapport(self, key: str, inhoud: bytes) -> str:
        """Bewaart een uitvoerbestand (bv. na het ophalen via reportUrl)."""
        naam = f"pipeline/{key}"
        if self.storage.exists(naam):
            self.storage.delete(naam)
        return self.storage.save(naam, ContentFile(inhoud))

    def bewaar_status(
        self, tekening_id: int, workitem_id: str, status: str, report_url: str | None = None
    ) -> None:
        tekening = Tekening.objects.get(pk=tekening_id)
        tekening.rapport = {
            **tekening.rapport,
            RAPPORT_SLEUTEL: {"workitem": workitem_id, "status": status, "reportUrl": report_url},
        }
        tekening.save(update_fields=["rapport"])
