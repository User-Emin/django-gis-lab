# Les 22: AutoCAD zonder scherm (prep-code)

Inhoud: `accoreconsole/` (lokale batch), `aps_da/` (DA v3-client, getest met gemockte HTTP),
`django-integratie/` (Celery-schets), `tests/`, `uitvoer/pytest.txt` (echte pytest-uitvoer, 13 passed), `bron/` (kopieën
van de gelezen bronnen). Bronnen per regel: `BRONNEN.md`.

> ⚠️ Niet uitgevoerd: geen Windows/AutoCAD op deze Mac (accoreconsole-scripts).
> ⚠️ Geen echte call naar APS gedaan: er zijn geen credentials. Alle tests gebruiken respx-mocks. Een echte run vraagt een
> APS-app met Design Automation, `APS_CLIENT_ID`/`APS_CLIENT_SECRET` in env en een geregistreerde nickname.

## Stroomschema
```
LOKAAL (Windows + AutoCAD-licentie)          CLOUD (APS Design Automation)
Celery-worker (Windows)                      Django-view -> Celery-task controleer_tekening
  batch.ps1: per *.dwg                         upload DWG naar opslag (signed URL)
  accoreconsole /i dwg /s rcs-batch.scr        POST /workitems  (nick.RcsCheckActivity+dev)
  NETLOAD RcsCheck.dll, RCSCHECK, QUIT         GET /workitems/{id} tot success/failed*
  -> logs/<naam>.log + batch.tsv (exitcode)    -> rapport via signed URL + reportUrl
```
Vergelijking met `10-route/img/schema/autocad-zonder-scherm.svg`: komt overeen (lokaal: worker op Windows, /i + /s,
log; cloud: view + Celery, upload, WorkItem, Activity met AppBundle, uitvoer via URL, "status ophalen of callback").
Verschil: de code doet alleen polling, geen callback (`onComplete` niet geverifieerd ⚠️); het SVG noemt "bewerkte DWG/DXF",
`rcs-batch.scr` slaat standaard niet op (variant `rcs-batch-qsave.scr` wel).

## Wanneer wat
- **accoreconsole lokaal / Windows-server**: tekeningen mogen het netwerk niet uit, er is al een AutoCAD-licentie en een
  Windows-machine, grote batches zonder verbruikskosten. Nadeel: zelf AutoCAD installeren en beheren.
- **Design Automation**: geen eigen Windows/AutoCAD-server, aanroep vanuit een Linux-Django-stack, pieken opvangen.
  Nadeel: Autodesk-account, verbruikskosten, bestanden gaan naar de cloud (signed URLs).

## Licenties en kosten
accoreconsole hoort bij een AutoCAD-installatie (licentie nodig); DA wordt per verbruik afgerekend.
⚠️ Prijsmodel onbevestigd (feiten-rvb-autocad B: alleen zoeksamenvatting "2,0 Flex-tokens per verwerkingsuur").

## Wat niet werkt in accoreconsole en DA
Geen COM/ActiveX (`vla-`/`vlax-`); basis-AutoLISP wel. `AutoCAD.NET` (AcMgd.dll) laat accoreconsole en DA crashen
(0xC0000005): gebruik `AutoCAD.NET.Core`. Geen dialogen (`FILEDIA 0`, `CMDDIA 0`), alle paden absoluut, uitvoer via
`Editor.WriteMessage` (komt in het DA-rapport). Bron: aps-lisp-dotnet-skill (BRONNEN.md).

## DWG lezen/schrijven zonder AutoCAD
- GDAL CAD-driver: alleen lezen (SPEC §9, les 20). ⚠️ driverpagina niet zelf opgehaald in deze run.
- ODA File Converter (DWG <-> DXF). ⚠️ niet geverifieerd in deze run.
- Via DA: AutoCAD-engine in de cloud leest en schrijft DWG (QSAVE naar `outputFile`, SKILL.md r164).

## Gebruik
`uv venv pipeline/.venv && uv pip install httpx respx pytest celery`, dan `.venv/bin/python -m pytest -v`.
