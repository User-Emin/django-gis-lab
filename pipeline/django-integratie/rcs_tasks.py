"""Schets: Celery-task voor les 22. De lab-agent zet dit in cad/tasks.py (Redis op 6390).

Waarom asynchroon: een workitem staat eerst in de wachtrij en draait daarna AutoCAD; de
Autodesk-sample pollt tot 300 s (APS-Common.ps1 Wait-WorkItem) en DA geeft per fase tijden
terug (stats.timeQueued … timeFinished). Een web-request mag daar niet op wachten.
⚠️ Een officiële typische duur ("seconden tot minuten") staat niet in de gelezen bronnen.
"""

from __future__ import annotations

from aps_da import FAILED_STATUSES, ApsClient, qualified_id
from celery import shared_task

ACTIVITY = "RcsCheckActivity"
ALIAS = "dev"


def voer_controle_uit(tekening_id: int, *, client, opslag, nickname: str) -> dict:
    """Kern zonder Django: ``opslag`` levert upload + signed URLs en bewaart het rapport."""
    in_url = opslag.upload_dwg(tekening_id)  # signed lees-URL
    uit_url = opslag.schrijf_url(f"rcs/{tekening_id}.json")  # signed schrijf-URL
    wi = client.start_workitem(
        qualified_id(nickname, ACTIVITY, ALIAS),
        {"inputFile": {"url": in_url}, "rapport": {"url": uit_url, "verb": "put"}},
    )
    opslag.bewaar_status(tekening_id, wi["id"], wi["status"])  # eerst id vastleggen (hervatbaar)
    r = client.wait_workitem(wi["id"], timeout=900)
    opslag.bewaar_status(tekening_id, wi["id"], r["status"], r.get("reportUrl"))
    if r["status"] in FAILED_STATUSES:
        raise RuntimeError(f"workitem {wi['id']}: {r['status']}")
    return r


@shared_task(bind=True, acks_late=True, max_retries=0)
def controleer_tekening(self, tekening_id: int) -> str:
    from django.conf import settings  # pas in de worker laden

    from cad.opslag import DjangoOpslag  # les 22: cad/opslag.py

    r = voer_controle_uit(
        tekening_id,
        client=ApsClient(),
        opslag=DjangoOpslag(),
        nickname=settings.APS_NICKNAME,
    )
    return r["status"]
