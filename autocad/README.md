# AutoCAD-voorbereiding les 21

Fictieve oefenplattegrond (`../data/cad/plattegrond-bg.dxf`, `../data/cad/plattegrond-bg-fouten.dxf`, fouten in `../data/cad/fouten.md`). Vier manieren om dezelfde RCS-laagcontrole + ruimtelijst te doen.

## Wanneer wat

| Aanpak | Vereist | Kan | Kan niet / let op | Bron |
|---|---|---|---|---|
| LISP / .scr (`lisp/`, `scr/`) | AutoCAD (of accoreconsole) op Windows | Basis-AutoLISP (`ssget`, `entget`, `tblnext`) werkt ook in accoreconsole; `.scr` stuurt accoreconsole via `/i` en `/s`, alle paden absoluut | Geen COM (`vla-`/`vlax-`) in accoreconsole; `.scr` heeft geen logica | `_spec/feiten-rvb-autocad.md` (AU-handout, SKILL.md; gezien 24-10-2026); accoreconsole-helppagina niet op te halen ⚠️ |
| .NET (`dotnet/`) | AutoCAD op Windows, `AutoCAD.NET.Core` (AcCoreMgd.dll) + Model; accoreconsole- en Design Automation-geschikt | Volledig objectmodel, `Polyline.Area` met bulges | Het pakket `AutoCAD.NET` (AcMgd.dll) crasht accoreconsole/DA (0xC0000005); compileren + NETLOAD | feiten-rvb-autocad.md; nuspec's api.nuget.org; `dotnet/API-BRONNEN.md` |
| COM / Python (`python-com/`) | Windows + draaiende AutoCAD + pywin32 (312, 04-06-2026) | Stuurt de open AutoCAD aan | Niet in accoreconsole/DA; pyautocad 0.2.0 is van 21-12-2015, niet meer bijgewerkt, werking met AutoCAD 2025+ ⚠️ niet getest | pypi.org/pypi/pywin32/json en /pyautocad/json (gezien 24-10-2026) |
| ezdxf (`python-ezdxf/`) | Alleen Python (+ shapely voor de extra controles); geen AutoCAD | Leest/schrijft DXF, werkt op Mac/Linux; eenvoudig te combineren met shapely/GEOS (overlap, geldigheid) | Alleen DXF, geen DWG (DWG eerst converteren) ⚠️ conversie-tool niet getest | Gedraaid in deze voorbereiding (`uitvoer/ezdxf-*.txt`); ezdxf 1.4.5, shapely 2.2.0 |

Controle-omvang: ezdxf-referentie doet 5 fouten uit `data/cad/fouten.md`. LISP/.scr, .NET en COM doen de controles overlap en `is_valid` BEWUST NIET; lesargument: Python + shapely (GEOS) doet dit goedkoop.

## Wat is echt gedraaid

| Onderdeel | Status | Bewijs |
|---|---|---|
| python-ezdxf/rcs_check.py (beide DXF's, incl. overlap + is_valid) | Gedraaid op Mac: foutloos 0 bevindingen, fouten-DXF 5 bevindingen (alle 5 uit fouten.md gevonden) | `uitvoer/ezdxf-plattegrond-bg*.txt` |
| Bulge-kruiscontrole ezdxf | Gedraaid | `uitvoer/ezdxf-bulge-*.txt` |
| python-com/rcs_check_com.py | Alleen guard gedraaid op Mac (py_compile + ruff check ok); ⚠️ COM-deel niet uitgevoerd | `uitvoer/com-guard-mac.txt` |
| lisp/rcs-check.lsp | Alleen haakjes-balans en functienamen in referentie gecontroleerd; ⚠️ niet in AutoCAD gedraaid | `uitvoer/lisp-haakjes.txt`, `lisp-functies-in-referentie.txt`; review `lisp/REVIEW.md` |
| scr/rcs-check.scr | ⚠️ niet gedraaid | n.v.t. |
| dotnet/RcsCheck | ⚠️ niet gecompileerd; API-namen (27) gevonden in XML-docs nupkg 25.0.0; PackageContents.xml goedgevormd | `uitvoer/api-check-nuget-xml.txt`, `uitvoer/xmllint.txt` |
| Ruff (`ruff check`) op alle Python-bestanden | Gedraaid, geen bevindingen | terminaluitvoer |

## In het lab

- Oefentekeningen: `data/cad/plattegrond-bg.dxf`, `data/cad/plattegrond-bg-fouten.dxf`, fouten in `data/cad/fouten.md`; bulge-demo: `autocad/testdata/bulge-demo.dxf`.
- Draaien: `uv run python autocad/python-ezdxf/rcs_check.py data/cad/plattegrond-bg-fouten.dxf`. `shapely` staat als dev-afhankelijkheid (alleen `rcs_check.py` gebruikt het; de Django-app niet).
- Tests: `autocad/tests/test_autocad_scripts.py`. De map `uitvoer/` uit de voorbereiding is niet overgenomen; de uitvoer staat in de lesbestanden (`_shots/txt/r21-*`).
- ⚠️ `dotnet` (SDK) is op deze machine niet aanwezig: `dotnet/RcsCheck` is niet gecompileerd.
