import pytest
from rcs_tasks import voer_controle_uit


class NepClient:
    def __init__(self, eind):
        self.eind, self.gestart = eind, None

    def start_workitem(self, act, args):
        self.gestart = (act, args)
        return {"id": "wi9", "status": "pending"}

    def wait_workitem(self, wid, timeout):
        return {"id": wid, "status": self.eind, "reportUrl": "https://r/9"}


class NepOpslag:
    def __init__(self):
        self.statussen = []

    def upload_dwg(self, tid):
        return f"https://s3/in/{tid}"

    def schrijf_url(self, key):
        return f"https://s3/uit/{key}"

    def bewaar_status(self, tid, wid, status, report=None):
        self.statussen.append((tid, wid, status, report))


def test_task_kern_success():
    c, o = NepClient("success"), NepOpslag()
    assert voer_controle_uit(5, client=c, opslag=o, nickname="rvb")["status"] == "success"
    assert c.gestart[0] == "rvb.RcsCheckActivity+dev"
    assert c.gestart[1]["rapport"]["verb"] == "put"
    assert o.statussen == [
        (5, "wi9", "pending", None),
        (5, "wi9", "success", "https://r/9"),
    ]


def test_task_kern_failed():
    o = NepOpslag()
    with pytest.raises(RuntimeError):
        voer_controle_uit(5, client=NepClient("failedInstructions"), opslag=o, nickname="rvb")
    assert o.statussen[-1][2] == "failedInstructions"
