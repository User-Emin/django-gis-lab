# RvbPostgis (AutoCAD 2020, net47)

Commando `RVBNAARPOSTGIS`: leest geselecteerde gesloten polylijnen (laag uit `rvbpostgis.conf`, standaard `92 Rust- en werkgebieden`), neemt EPSG:28992 aan en schrijft ze met Npgsql, in één transactie en met parameters, naar `cad_ruimte_import` (`sql/cad_ruimte_import.sql`).

- Verbinding: omgevingsvariabele `RVB_PG_CONNECTION` of `ConnectionString=...` in `rvbpostgis.conf` naast de DLL. Nooit in de tekening (RCS: geen databasekoppelingen in dwg).
- Laden: `NETLOAD` met `RvbPostgis.dll` (map met Npgsql-DLL's ernaast). ⚠️ Geen `PackageContents.xml`-bundel: het formaat voor 2020 is in de feiten niet bevestigd. Een "trusted" map kan nodig zijn.
- ⚠️ Gebouwd en getest in CI (windows-latest); niet in AutoCAD uitgevoerd.
- Bogen (bulge) worden afgekeurd; punten buiten het RD-bereik (lokale coördinaten) ook.
