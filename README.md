# django-gis-lab: Projectkaart

Praktijklab bij de Django-GIS-kennisbank (lessen over Django, PostGIS, OpenLayers en AutoCAD/DXF in een GIS-pipeline). Het is een werkende app voor ontwerptekeningen (DXF) van een herinrichting in Almere. Elke les in de kennisbank heeft een tag in deze repo: `git checkout les-NN`.

**Alleen open data.** BAG-panden (PDOK, CC0) en CBS-buurten (CC BY 4.0), plus een zelf gegenereerde, fictieve plattegrond. Geen echte tekeningen van derden, geen credentials. Zie `THIRD_PARTY.md` voor herkomst en licenties; code staat onder de MIT-licentie (`LICENSE`).

## Draaien

Nodig: [uv](https://docs.astral.sh/uv/), PostgreSQL met PostGIS op poort 5433 (database `djangolab`), Redis op poort 6390 (alleen voor Celery, les 22), GDAL/GEOS op het systeem.

```
cp .env.example .env     # eigen waarden invullen; .env staat in .gitignore
uv sync
uv run python manage.py migrate
uv run python manage.py runserver 127.0.0.1:8700
set -a; . ./.env; set +a; uv run pytest -q
```

Meewerken: zie `CONTRIBUTING.md`.

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
| les-20 | Terug naar CAD: `exporteer_dxf` (GIS naar DXF met RCS-laagnamen, inverse georef, `$INSUNITS`), rondreis, `ogr2ogr -f DXF` ter vergelijking, DWG (CAD-driver alleen lezen) |
| les-21 | AutoCAD automatiseren: `autocad/` met RCS-laagcontrole in LISP, `.scr`, .NET (niet gecompileerd), COM (alleen Windows) en Python/ezdxf (shapely: overlap, is_valid), bulge-oppervlakte |
| les-22 | AutoCAD in de pipeline: `pipeline/` (accoreconsole-batch, APS Design Automation-client met respx-tests, Django-schets), `cad/opslag.py`, Celery + Redis (poort 6390) met `cad.rcs_check` en een taakstatuspagina |

Database: PostgreSQL op 127.0.0.1:5433, database `djangolab`.
