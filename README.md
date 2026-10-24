# django-gis-lab: Projectkaart

Oefenproject bij de Django-GIS-kennisbank: een app voor ontwerptekeningen (DXF) van een herinrichting in Almere.
Elke les heeft een tag: `git checkout les-NN`.

| Tag | Stand |
|---|---|
| les-01..03 | begin: README, .gitignore, .env.example |
| les-04 | uv-project, ruff, pre-commit, logging |
| les-05 | Django 6.1 (les 05 legt LTS 5.2 vs feature-release 6.1 uit)-project, settings per omgeving |
| les-06 | app `kaart`: modellen, migraties, debug-toolbar, N+1 |
| les-07 | views, templates, formulier met validatie en CSRF |
| les-08 | pytest-django, factory-boy, coverage |
| les-11 | ruimtelijke lookups, dwithin (RD en geography), Distance, EXPLAIN met/zonder GiST |
| les-15 | Vite-build naar Django static, tekenen (ol Draw) en opslaan met POST + CSRF |
| les-16 | vector tiles uit PostGIS (ST_AsMVT, RD-tegels op het PDOK-grid via ST_TileEnvelope met bounds), OL VectorTile achter `?panden=tiles`, cache |
| les-17 | DXF van binnen: ezdxf (HEADER/TABLES/BLOCKS/ENTITIES), `$INSUNITS`, bulge, ruimtes uit laag 92, `manage.py dxf_inhoud` (oefendata in `data/cad/`) |
| les-18 | DXF importeren: upload-formulier (multipart), `importeer_dxf` met rapport, eigen SRID 990001 voor tekeningcoördinaten, GDAL `ogr2ogr` ter vergelijking, tekening-kaart in OpenLayers |
| les-19 | Georeferentie en kwaliteit: paspunten, affien vs Helmert (`georefereer`), `ST_Affine`, `geom_rd` in RD op PDOK, `controleer_tekening` (ST_IsValid, ST_MakeValid, overlap, pand-verschil, EXPLAIN) |

Starten: `cp .env.example .env`, `uv sync`, `uv run python manage.py runserver 127.0.0.1:8700`.
Database: PostgreSQL op 127.0.0.1:5433, database `djangolab`.
