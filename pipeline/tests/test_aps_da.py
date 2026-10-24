import base64
import logging
from urllib.parse import parse_qs

import httpx
import pytest
import respx
from aps_da import (
    AUTH_URL,
    ApsClient,
    ApsError,
    WorkItemTimeout,
    qualified_id,
    rcs_activity_spec,
)

GEHEIM = "s3cr3t-NIET-LOGGEN"
TOKEN = "tok-ABC-geheim"
DA = "https://developer.api.autodesk.com/da/us-east/v3"


@pytest.fixture
def client():
    return ApsClient("mijn-id", GEHEIM, sleep=lambda s: None)


def token_route(mock):
    return mock.post(AUTH_URL).mock(
        return_value=httpx.Response(200, json={"access_token": TOKEN, "expires_in": 3600})
    )


@respx.mock
def test_token_ophalen_basic_auth_en_scopes(client):
    route = token_route(respx)
    assert client.token() == TOKEN
    assert client.token() == TOKEN  # gecachet
    assert route.call_count == 1
    req = route.calls[0].request
    assert (
        req.headers["Authorization"]
        == "Basic " + base64.b64encode(f"mijn-id:{GEHEIM}".encode()).decode()
    )
    form = parse_qs(req.content.decode())
    assert form["grant_type"] == ["client_credentials"]
    assert "code:all" in form["scope"][0].split()


@respx.mock
def test_workitem_request_vorm(client):
    token_route(respx)
    route = respx.post(f"{DA}/workitems").mock(
        return_value=httpx.Response(200, json={"id": "wi1", "status": "pending"})
    )
    act = qualified_id("rvbnick", "RcsCheckActivity", "dev")
    args = {
        "inputFile": {"url": "https://s3/in?sig=1"},
        "rapport": {"url": "https://s3/uit?sig=2", "verb": "put"},
    }
    assert client.start_workitem(act, args)["id"] == "wi1"
    req = route.calls[0].request
    assert req.headers["Authorization"] == f"Bearer {TOKEN}"
    import json

    assert json.loads(req.content) == {
        "activityId": "rvbnick.RcsCheckActivity+dev",
        "arguments": args,
    }


def test_activityid_moet_volledig_zijn(client):
    with pytest.raises(ValueError):
        client.start_workitem("RcsCheckActivity", {})


def test_activity_spec_gebruikt_al_en_appbundle():
    spec = rcs_activity_spec("rvbnick")
    assert spec["appbundles"] == ["rvbnick.RcsCheck+dev"]
    assert '/al "$(appbundles[RcsCheck].path)"' in spec["commandLine"][0]
    assert spec["engine"] == "Autodesk.AutoCAD+25_0"


@pytest.mark.parametrize("eind", ["success", "failedInstructions"])
@respx.mock
def test_polling_stopt_bij_eindstatus(client, eind):
    token_route(respx)
    route = respx.get(f"{DA}/workitems/wi1").mock(
        side_effect=[
            httpx.Response(200, json={"id": "wi1", "status": "pending"}),
            httpx.Response(200, json={"id": "wi1", "status": "inprogress"}),
            httpx.Response(
                200,
                json={"id": "wi1", "status": eind, "reportUrl": "https://r/rep.txt"},
            ),
        ]
    )
    r = client.wait_workitem("wi1", interval=0)
    assert r["status"] == eind and r["reportUrl"] == "https://r/rep.txt"
    assert route.call_count == 3


@respx.mock
def test_polling_timeout(client):
    token_route(respx)
    respx.get(f"{DA}/workitems/wi1").mock(
        return_value=httpx.Response(200, json={"id": "wi1", "status": "pending"})
    )
    t = iter(range(100))
    with pytest.raises(WorkItemTimeout):
        client.wait_workitem("wi1", timeout=3, interval=0, clock=lambda: next(t))


@respx.mock
def test_429_wordt_herhaald_met_backoff():
    wachttijden = []
    c = ApsClient("mijn-id", GEHEIM, sleep=wachttijden.append)
    token_route(respx)
    route = respx.post(f"{DA}/workitems").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "7"}),
            httpx.Response(429),
            httpx.Response(200, json={"id": "wi1", "status": "pending"}),
        ]
    )
    assert c.start_workitem("n.A+dev", {})["id"] == "wi1"
    assert route.call_count == 3 and wachttijden == [7.0, 2]


@respx.mock
def test_post_wordt_niet_herhaald_bij_500(client):
    token_route(respx)
    route = respx.post(f"{DA}/workitems").mock(return_value=httpx.Response(500))
    with pytest.raises(ApsError):
        client.start_workitem("n.A+dev", {})
    assert route.call_count == 1  # geen dubbel workitem


@respx.mock
def test_geheim_nooit_in_log_of_exception(client, caplog):
    caplog.set_level(logging.DEBUG)
    token_route(respx)
    respx.get(f"{DA}/workitems/x").mock(
        return_value=httpx.Response(403, text=f"bad token {TOKEN} for secret {GEHEIM}")
    )
    with pytest.raises(ApsError) as exc:
        client.workitem("x")
    for tekst in (str(exc.value), caplog.text, repr(client)):
        assert GEHEIM not in tekst and TOKEN not in tekst


def test_zonder_env_geen_client(monkeypatch):
    monkeypatch.delenv("APS_CLIENT_ID", raising=False)
    monkeypatch.delenv("APS_CLIENT_SECRET", raising=False)
    with pytest.raises(ValueError):
        ApsClient()
