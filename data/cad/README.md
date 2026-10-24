# Oefendata deel E: plattegrond-bg (fictief)

**Fictieve oefenplattegrond, geen echt rijksgebouw.** De plattegrond is verzonnen; alleen de contour komt van een echt pand.

## Herkomst pand
BAG-pand `0034100000049762` (kantoor, bouwjaar 2002, 878 m2, vrijwel vierkant, 6 hoekpunten), gelezen op 24-10-2026 uit `~/django-lab/data/almere.gpkg` (laag panden; BAG via PDOK); de hoekpunten staan in `pand.json`. Lokale oorsprong zo gekozen dat hoekpunt B op (500,500) mm ligt.

## Bestanden
| Bestand | Inhoud |
|---|---|
| `plattegrond-bg.dxf` | foutloze plattegrond, AC1032, 1 unit = 1 mm, INSUNITS=4, 1e kwadrant |
| `plattegrond-bg-fouten.dxf` | zelfde plattegrond met 5 bewuste fouten, zie `fouten.md` |
| `pand.json` | pandgegevens en BAG-herkomst |
| `georef-waarheid.json` | affiene transformatie lokaal (mm) naar RD (EPSG:28992, m), paspunten; de waarheid voor georefereren |
| `gen/gen_plattegrond.py` | generator (ezdxf), schrijft DXF's, json en renders |
| `gen/inhoud_hash.py` | sha256 over de inhoud (type, laag, coordinaten op 0,01 mm, tekst, attribs) |
| `fouten.md` | de 5 fouten, detectie, verwachte uitkomst |

## Laagnamen en bronstatus
Syntax uit de RCS (§1.4): `<NL/SfB-code, 2 cijfers><spatie><omschrijving>`. De RCS bevat zelf geen laagnamenlijst en het RVB BIM- en CAD-protocol v1.0 (24-11-2022) ook niet (geen treffers op laag/layer/NL-SfB).
| Laag | Status |
|---|---|
| `0` | RCS p. 12: alleen INSERTs van block RUIMTELABEL |
| `21 Buitenwanden`, `22 Binnenwanden` | bevestigd: NL/SfB 2005 tabel 1 (BNA), https://stprodeuwmystabu002stor.blob.core.windows.net/overig/NL-SfB_BNA_Boek_2005-ISBN-10%2090-807626-3-6.pdf, en https://www.modelleerafspraken.nl/index.php/bijlagen/bijlage-nl-sfb-2-cijfers (beide gezien 24-10-2026) |
| `31 Buitenwandopeningen`, `32 Binnenwandopeningen` | bevestigd: zelfde twee bronnen |
| `92 Rust- en werkgebieden` | tabel 0 (ruimtelijke voorzieningen) van NL/SfB 2005: code 92; RCS vraagt voor ruimtenaam/-code een tekstlaag volgens tabel 0. Ruimtecontour, code en naam staan op deze laag. Keuze van code 92 voor een kantoor is eigen interpretatie van de tabel |
| `99 Maatvoering`, `99 Tekst` | ⚠️ eigen keuze; 99 is "gereserveerd" in tabel 1, geen bron voor deze namen |
| `Defpoints` | automatisch, leeg |
| `Ruimten` (alleen in fouten-DXF) | bewust fout, geen code |

## Regenereren
```
cd ~/django-lab
uv run python data/cad/gen/gen_plattegrond.py
uv run python -I data/cad/gen/inhoud_hash.py data/cad/plattegrond-bg.dxf data/cad/plattegrond-bg-fouten.dxf
```
De generator is deterministisch; de inhoud-hash is de toets. De RCS-PDF en de tussenuitvoer (audit, ogrinfo) uit de voorbereiding zijn niet meegenomen; zie `data/README.md` voor de RCS-URL.
