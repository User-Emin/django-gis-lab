# Third party: herkomst en licenties

Eigen code en eigen tekst staan onder MIT (`LICENSE`). Hieronder alles wat van elders komt (gecontroleerd 24-10-2026).

| Bestand(en) | Herkomst | Licentie |
|---|---|---|
| `data/almere.gpkg`, laag `panden` | BAG via PDOK (Kadaster), https://www.pdok.nl/ | CC0 / open data |
| `data/almere.gpkg`, laag `buurten` | Wijk- en buurtkaart, CBS via PDOK, https://www.pdok.nl/ | CC BY 4.0 (bronvermelding: CBS) |
| `data/cad/plattegrond-bg.dxf`, `plattegrond-bg-fouten.dxf`, `pand.json`, `georef-waarheid.json` | Zelf gegenereerd met `data/cad/gen/gen_plattegrond.py` (ezdxf). Fictieve indeling; alleen de buitencontour is van BAG-pand 0034100000049762 (CC0) | MIT (eigen werk), contour CC0 |
| `autocad/testdata/bulge-demo.dxf` | Zelf gegenereerd met `autocad/python-ezdxf/maak_bulge_demo.py` | MIT (eigen werk) |
| `pipeline/bron/dadotnet-DesignAutomationController.cs` | https://github.com/autodesk-platform-services/aps-design-automation-dotnet | MIT, (c) Autodesk |
| `pipeline/bron/sdk-Configuration.gen.cs`, `sdk-Status.gen.cs` | https://github.com/Autodesk-Forge/forge-api-dotnet-design.automation (`src/Autodesk.Forge.DesignAutomation`) | Apache-2.0, (c) Autodesk; licentiekop staat in de bestanden zelf, tekst op http://www.apache.org/licenses/LICENSE-2.0 |
| Python-afhankelijkheden (ezdxf, shapely, Django, enz.) | Niet meegeleverd, via `uv.lock` | eigen licenties van de pakketten (ezdxf: MIT) |
| RCS-laagnamen (RVB CAD Specificatie v1.01) | Alleen de syntax is gevolgd; de PDF is niet meegeleverd | CC BY-NC-SA 4.0 |

## Niet meegeleverd

Elf bestanden uit https://github.com/autodesk-platform-services/aps-lisp-dotnet-skill (commit 23e88934d1661116683e39a4041318a9e9d80c03) staan niet in deze repo: geen licentie in de bronrepo (gh api license=null, 24-10-2026). Zie `pipeline/BRONNEN.md`.

Voorbeelden in `autocad/` zijn eigen werk. De GDAL-autotest wordt niet gebruikt of meegeleverd; GDAL/ogr2ogr wordt alleen als programma aangeroepen.
