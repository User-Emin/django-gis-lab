"""APS Design Automation v3-client (httpx).

Idempotentie
    DA maakt bij elke ``POST /workitems`` een nieuw workitem (dus nieuw verbruik). Een POST die een
    5xx of time-out krijgt, weet je niet of hij is aangekomen. Daarom: GET en DELETE worden bij
    429/5xx herhaald, POST alleen bij 429 (de server heeft het verzoek dan geweigerd, niet
    uitgevoerd). ``POST /appbundles`` en ``/activities`` zijn wel veilig te herhalen: een tweede
    keer geeft 409 en dan maakt deze client een nieuwe versie (``/{id}/versions``), net als
    APS-Common.ps1 in aps-lisp-dotnet-skill. Bewaar het workitem-id (bijv. in de database) voordat
    je gaat pollen; een herstart pollt dan verder in plaats van opnieuw te starten.
Retries
    Exponentiële backoff (1, 2, 4, 8 s, max ``max_retries``); een ``Retry-After``-header in seconden
    gaat voor. ⚠️ Of DA bij 429 ``Retry-After`` meestuurt, staat niet in de gelezen bronnen.
Polling
    ``GET /workitems/{id}`` tot de status niet meer ``pending``/``inprogress`` is, met een harde
    time-out (``WorkItemTimeout``). Interval 5 s zoals de Autodesk-sample.
Geheimen
    Client-secret en token komen nooit in logs, ``repr`` of exceptions: logging toont alleen
    methode, pad en status; foutmeldingen worden geschoond.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

log = logging.getLogger("aps_da")

AUTH_URL = "https://developer.api.autodesk.com/authentication/v2/token"
DA_URL = "https://developer.api.autodesk.com/da/{region}/v3"
SCOPES = (
    "code:all",
    "data:read",
    "data:write",
    "bucket:create",
    "bucket:read",
    "bucket:update",
)
RUNNING_STATUSES = frozenset({"pending", "inprogress"})
FAILED_STATUSES = frozenset(
    {
        "cancelled",
        "failedLimitDataSize",
        "failedLimitProcessingTime",
        "failedDownload",
        "failedInstructions",
        "failedUpload",
        "failedUploadOptional",
    }
)
RETRY_STATUS = frozenset({429, 500, 502, 503, 504})


class ApsError(Exception):
    def __init__(self, method: str, path: str, status: int, detail: str = ""):
        self.method, self.path, self.status = method, path, status
        super().__init__(f"APS {method} {path} -> {status} {detail}".rstrip())


class WorkItemTimeout(Exception):
    pass


def qualified_id(nickname: str, name: str, alias: str) -> str:
    """``<nickname>.<id>+<alias>``, zoals DA een activity of appbundle volledig noemt."""
    return f"{nickname}.{name}+{alias}"


def rcs_activity_spec(
    nickname: str,
    *,
    activity: str = "RcsCheckActivity",
    bundle: str = "RcsCheck",
    alias: str = "dev",
    engine: str = "Autodesk.AutoCAD+25_0",
) -> dict[str, Any]:
    """Activity voor RCSCHECK. Vorm volgt activity.json (FlangeDA) en de DA-controller."""
    return {
        "id": activity,
        "engine": engine,
        "appbundles": [qualified_id(nickname, bundle, alias)],
        "commandLine": [
            "".join(
                [
                    '$(engine.path)\\accoreconsole.exe /i "$(args[inputFile].path)" ',
                    f'/al "$(appbundles[{bundle}].path)" /s "$(settings[script].path)"',
                ]
            )
        ],
        "parameters": {
            "inputFile": {
                "verb": "get",
                "required": True,
                "localName": "input.dwg",
                "description": "Te controleren tekening",
            },
            "rapport": {
                "verb": "put",
                "required": True,
                "localName": "rcs-rapport.json",
                "description": "Uitvoer van RCSCHECK (naam bepaald door les 21)",
            },
        },
        "settings": {"script": {"value": "RCSCHECK\n"}},
        "description": "RCS-controle van een DWG, zonder scherm",
    }


class ApsClient:
    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        *,
        region: str = "us-east",
        scopes: tuple[str, ...] = SCOPES,
        http: httpx.Client | None = None,
        max_retries: int = 4,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._id = client_id or os.environ.get("APS_CLIENT_ID", "")
        self._secret = client_secret or os.environ.get("APS_CLIENT_SECRET", "")
        if not self._id or not self._secret:
            raise ValueError("APS_CLIENT_ID en APS_CLIENT_SECRET ontbreken")
        self.da_url = DA_URL.format(region=region)
        self.scopes = scopes
        self._http = http or httpx.Client(timeout=30)
        self._max_retries = max_retries
        self._sleep = sleep
        self._token: str | None = None
        self._token_until = 0.0

    def __repr__(self) -> str:
        return f"ApsClient(client_id={self._id[:4]}…, region={self.da_url})"

    # --- intern -------------------------------------------------------------------------
    def _clean(self, text: str) -> str:
        for geheim in (self._secret, self._token):
            if geheim:
                text = text.replace(geheim, "***")
        return text[:300]

    def _send(self, method: str, url: str, **kw: Any) -> httpx.Response:
        path = httpx.URL(url).path
        for poging in range(self._max_retries + 1):
            try:
                resp = self._http.request(method, url, **kw)
            except httpx.TransportError as exc:
                if method != "GET" or poging == self._max_retries:
                    raise ApsError(method, path, 0, type(exc).__name__) from None
                self._sleep(2**poging)
                continue
            log.info("APS %s %s -> %s", method, path, resp.status_code)
            herhaalbaar = resp.status_code == 429 or (
                method in ("GET", "DELETE") and resp.status_code >= 500
            )
            if resp.status_code in RETRY_STATUS and herhaalbaar and poging < self._max_retries:
                wacht = resp.headers.get("Retry-After", "")
                self._sleep(float(wacht) if wacht.isdigit() else 2**poging)
                continue
            if resp.is_error:
                raise ApsError(method, path, resp.status_code, self._clean(resp.text))
            return resp
        raise AssertionError("onbereikbaar")

    def token(self) -> str:
        if self._token and time.time() < self._token_until:
            return self._token
        resp = self._send(
            "POST",
            AUTH_URL,
            auth=(self._id, self._secret),  # HTTP Basic, zoals APS-Common.ps1
            data={"grant_type": "client_credentials", "scope": " ".join(self.scopes)},
        )
        body = resp.json()
        self._token = body["access_token"]
        self._token_until = time.time() + int(body.get("expires_in", 0)) - 60
        return self._token

    def _da(self, method: str, path: str, json: Any = None) -> Any:
        resp = self._send(
            method,
            f"{self.da_url}/{path}",
            json=json,
            headers={"Authorization": f"Bearer {self.token()}"},
        )
        return resp.json() if resp.content else None

    # --- appbundles en activities ---------------------------------------------------------
    def nickname(self) -> str:
        """``GET /forgeapps/me``; antwoord is een kale JSON-string (SKILL.md r135) of {id}."""
        r = self._da("GET", "forgeapps/me")
        return r if isinstance(r, str) else r["id"]

    def create_appbundle(self, bundle_id: str, engine: str, description: str = "") -> dict:
        body = {"id": bundle_id, "engine": engine, "description": description}
        try:
            return self._da("POST", "appbundles", body)
        except ApsError as e:
            if e.status != 409:
                raise
            body.pop("id")
            return self._da("POST", f"appbundles/{bundle_id}/versions", body)

    def upload_appbundle(self, upload_parameters: dict, zip_path: Path) -> None:
        """Multipart-POST naar ``endpointURL`` met alle ``formData``-velden en daarna ``file``."""
        with open(zip_path, "rb") as f:
            self._send(
                "POST",
                upload_parameters["endpointURL"],
                data=upload_parameters["formData"],
                files={"file": (Path(zip_path).name, f, "application/octet-stream")},
            )

    def create_appbundle_alias(self, bundle_id: str, alias: str, version: int) -> dict:
        return self._da(
            "POST", f"appbundles/{bundle_id}/aliases", {"id": alias, "version": version}
        )

    def create_activity(self, spec: dict) -> dict:
        try:
            return self._da("POST", "activities", spec)
        except ApsError as e:
            if e.status != 409:
                raise
            rest = {k: v for k, v in spec.items() if k != "id"}
            return self._da("POST", f"activities/{spec['id']}/versions", rest)

    def create_activity_alias(self, activity_id: str, alias: str, version: int) -> dict:
        return self._da(
            "POST",
            f"activities/{activity_id}/aliases",
            {"id": alias, "version": version},
        )

    # --- workitems -------------------------------------------------------------------------
    def start_workitem(self, activity_id: str, arguments: dict[str, dict]) -> dict:
        """``activity_id`` volledig (``nick.Activity+alias``); per argument ``url`` en optioneel
        ``verb`` (get/put) en ``headers``, zoals XrefTreeArgument in de Autodesk-sample."""
        if "." not in activity_id or "+" not in activity_id:
            raise ValueError("activityId moet de vorm <nickname>.<activity>+<alias> hebben")
        return self._da("POST", "workitems", {"activityId": activity_id, "arguments": arguments})

    def workitem(self, workitem_id: str) -> dict:
        return self._da("GET", f"workitems/{workitem_id}")

    def wait_workitem(
        self,
        workitem_id: str,
        *,
        timeout: float = 600,
        interval: float = 5,
        clock: Callable[[], float] = time.monotonic,
    ) -> dict:
        eind = clock() + timeout
        while True:
            r = self.workitem(workitem_id)
            if r["status"] not in RUNNING_STATUSES:
                return r
            if clock() >= eind:
                raise WorkItemTimeout(f"workitem {workitem_id} na {timeout}s nog {r['status']}")
            self._sleep(interval)
