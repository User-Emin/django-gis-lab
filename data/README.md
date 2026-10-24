# Data

`almere.gpkg` (2,4 MB, EPSG:28992): subset van Almere Stad-centrum, gemaakt met `scripts/maak_almere_gpkg.sh`.

| Laag | Inhoud | Bron | Licentie |
|---|---|---|---|
| `panden` | BAG-panden (5.726) | BAG via PDOK (Kadaster) | CC0 / open data |
| `buurten` | CBS-buurten (31) die het gebied raken | Wijk- en buurtkaart CBS via PDOK | CC BY 4.0 (CBS) |

Het script leest uit een lokale database (`geolab`); wie die niet heeft, kan het bestand uit de repo gebruiken.

## `cad/` (les 17: DXF van binnen)

Fictieve oefenplattegrond, geen echt rijksgebouw: een kantoorverdieping met 11 ruimtes.

- Herkomst: `plattegrond-bg.dxf` en `plattegrond-bg-fouten.dxf` zijn gegenereerd door `data/cad/gen/gen_plattegrond.py` (ezdxf, deterministisch: `gen/inhoud_hash.py` geeft dezelfde inhoud-hash bij elke run). Alleen de buitencontour komt van een echt pand: BAG-pand `0034100000049762` uit `almere.gpkg` (BAG via PDOK, CC0), vastgelegd in `cad/pand.json`. De indeling is verzonnen.
- `cad/georef-waarheid.json`: affiene transformatie lokaal (mm) naar RD (EPSG:28992); `cad/fouten.md`: de 5 bewuste fouten in de fouten-DXF.
- Laagnamen volgen de RVB CAD Specificatie (RCS) v1.01 (juli 2019, CC BY-NC-SA 4.0): https://www.tenderned.nl/papi/tenderned-rs-tns/v2/publicaties/247191/documenten/7399721/content
- De RCS-PDF zelf is niet meegenomen in deze repo (licentie en omvang); download hem via de URL hierboven.
- Regenereren: `uv run python data/cad/gen/gen_plattegrond.py`
