"""Wacht tot SonarQube de analyse heeft verwerkt en lees de kwaliteitspoort.

Gebruik in de pipeline (les 31) na `pysonar`:
    SONAR_TOKEN=... uv run python scripts/sonar_gate.py

Exit 0 bij status OK, 1 bij ERROR of een time-out. Geen extra Jenkins-plugin en geen webhook nodig.
"""

import base64
import json
import os
import sys
import time
import urllib.request

REPORT = ".scannerwork/report-task.txt"


def haal(url: str, token: str) -> dict:
    auth = base64.b64encode(f"{token}:".encode()).decode()
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req, timeout=30) as antwoord:  # noqa: S310
        return json.load(antwoord)


def main() -> int:
    token = os.environ["SONAR_TOKEN"]
    taak = dict(r.strip().split("=", 1) for r in open(REPORT) if "=" in r)
    host = taak["serverUrl"]
    for _ in range(60):
        ce = haal(f"{host}/api/ce/task?id={taak['ceTaskId']}", token)["task"]
        print(f"CE-taak {ce['id']}: {ce['status']}")
        if ce["status"] in ("SUCCESS", "FAILED", "CANCELED"):
            break
        time.sleep(5)
    if ce["status"] != "SUCCESS":
        print("Analyse niet verwerkt")
        return 1
    url = f"{host}/api/qualitygates/project_status?analysisId={ce['analysisId']}"
    poort = haal(url, token)["projectStatus"]
    print(f"Quality gate: {poort['status']}")
    for c in poort["conditions"]:
        waarde, drempel = c.get("actualValue"), c.get("errorThreshold")
        print(f"  {c['metricKey']}: {c['status']} (waarde {waarde}, drempel {drempel})")
    return 0 if poort["status"] == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
