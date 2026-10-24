# Bewuste fouten in plattegrond-bg-fouten.dxf

Fictieve oefenplattegrond. `plattegrond-bg.dxf` is de foutloze variant; `plattegrond-bg-fouten.dxf` bevat precies deze vijf fouten.
Ruimtenummers zijn `00.<volgnr>`. Alle ruimten staan op laag `92 Rust- en werkgebieden` als gesloten LWPOLYLINE.
Lokale mm-coordinaten (1e kwadrant); in PostGIS na georefereren (zie georef-waarheid.json) is de oppervlakte in m2.

| # | Ruimte | Wat er mis is | Detectie | Verwachte uitkomst |
|---|---|---|---|---|
| 1 | 00.04 (Kantoor) | Polygoon niet gesloten: `closed=False`, laatste punt valt niet op eerste | ezdxf: `e.closed` is False voor een LWPOLYLINE op de ruimtelaag. GEOS/PostGIS: `ST_IsClosed(ST_GeomFromText('LINESTRING(...)'))` is false; `ST_BuildArea`/`ST_MakePolygon` faalt of geeft NULL | 1 open ruimtecontour; ruimte 00.04 heeft geen oppervlakte |
| 2 | 00.03 (Vergaderruimte) | Contour 1500 mm te ver naar links: overlapt 00.02 | GEOS/PostGIS: `ST_Overlaps(a,b)` of `ST_Area(ST_Intersection(a,b)) > 0` over alle paren op de ruimtelaag; shapely: `a.intersection(b).area` | 1 paar (00.02, 00.03) met overlap van ongeveer 1500 mm x ruimtebreedte (ca. 1500 mm x 8 m, circa 12 m2); in de goede DXF 0 paren (alleen aanraking via wanddikte, ruimten sluiten op wandvlak) |
| 3 | 00.10 (Toilet) | Contour op laag `Ruimten`; voldoet niet aan RCS-syntax (`<2 cijfers><spatie><omschrijving>`) | ezdxf: laagnamen toetsen met regex `^\d{2} [\w\- ]+$` (laag `0` en `Defpoints` uitgezonderd); ogrinfo: `GROUP BY Layer` toont laag `Ruimten` | 1 laagnaam die niet voldoet: `Ruimten`; de teksten van 00.10 staan wel op de goede laag |
| 4 | 00.11 (Pantry) | Ruimte zonder nummer: ATTRIB RUIMTENR is leeg en er is geen TEXT met de code | ezdxf: INSERT RUIMTELABEL met `attrib.dxf.text == ""`; tel TEXT-codes per ruimte (puntinpolygoon). PostGIS: ruimtepolygoon zonder label-punt met niet-lege code binnen `ST_Contains` | 1 ruimte zonder code; 11 polygonen maar 10 codes |
| 5 | 00.06 (Archief) | Bowtie: twee hoekpunten verwisseld, de contour snijdt zichzelf | GEOS/PostGIS: `ST_IsValid(geom)` is false, `ST_IsValidReason` = "Self-intersection"; shapely `explain_validity`; `ST_Area` van de bowtie is bijna 0 (twee driehoeken heffen elkaar op) | 1 ongeldige geometrie; `ST_MakeValid` geeft een MultiPolygon van twee driehoeken |

Controle: `ezdxf.audit` en ogrinfo melden geen van deze fouten als bestandsfout (0 audit-fouten); het zijn inhoudelijke tekenfouten.
In de goede DXF geeft elke bovenstaande controle 0 treffers.
