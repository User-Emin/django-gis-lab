> ⚠️ Niet gecompileerd op deze Mac

# RcsCheck (.NET)

Commando `RCSCHECK`: dezelfde laag- en ruimtecontrole als `lisp/rcs-check.lsp`, als AutoCAD.NET.Core-bibliotheek (geschikt voor accoreconsole en Design Automation, geen UI).

- Bestanden: `RcsCheck/RcsCheck.csproj` (Core + Model 25.0.0, net8.0-windows), `RcsCheck/Commands.cs`, `RcsCheck/PackageContents.xml`.
- Wat is gecontroleerd: de API-namen (zie `API-BRONNEN.md`) en dat `PackageContents.xml` goed gevormd is (`../uitvoer/xmllint.txt`). Compileren, laden met NETLOAD en draaien in AutoCAD: ⚠️ niet gedaan (geen dotnet, geen AutoCAD op deze Mac).
- Gebruik (⚠️ ongetest): `dotnet build -c Release` op Windows, dan in AutoCAD `NETLOAD` + `RCSCHECK`, of via accoreconsole `/i` + `/s` met absolute paden.
- Verschil met de LISP-versie: `Polyline.Area` neemt bulges mee (LISP-shoelace niet).
- Deze versie doet NIET de twee extra controles uit de Python-referentie (overlap tussen ruimten, ongeldige/zelfsnijdende geometrie). Bewuste keuze: dat is het lesargument voor Python + shapely/GEOS.
