# Tekstuele review lisp/rcs-check.lsp

> ⚠️ Alleen gelezen, niet in AutoCAD uitgevoerd. Haakjes-balans wel machinaal gecontroleerd (`uitvoer/lisp-haakjes.txt`); alle 33 gebruikte functies bestaan in de AutoLISP-referentie 2026 (`uitvoer/lisp-functies-in-referentie.txt`, bron `llms-autolisp.txt` van autodesk-platform-services).

| # | Punt | Uitwerking | Status |
|---|---|---|---|
| 1 | `wcmatch naam "##*"` | `#` = één cijfer. Zo gebruikt in `rcs:laagnaam-ok`. In `llms-autolisp.txt` heeft de wcmatch-pagina (GUID-EC257AF7-...) alleen een titel, geen inhoud; de betekenis komt uit kennis. | ⚠️ niet in referentietekst teruggevonden |
| 2 | `wcmatch tekst "##`.##"` | `` ` `` = escape: het volgende teken (hier de punt) letterlijk, anders is `.` een willekeurig teken-wildcard (`.` = elk niet-alfanumeriek teken, uit kennis). Zonder escape zou ook "00-01" matchen. | ⚠️ idem |
| 3 | `rtos` en DIMZIN | De oppervlakte-uitvoer gebruikt `(rtos x 2 2)`. Het resultaat (decimaalteken, nullen achteraan) hangt mogelijk af van DIMZIN en de regio-instelling; uit kennis, niet gecontroleerd ⚠️. in de CSV (`;` als scheiding) kan een komma-decimaal tot verwarring leiden. Testen op een Nederlandse Windows. | ⚠️ |
| 4 | `open`/`write-line` naast de DWG | Uitvoer gaat naar `DWGPREFIX` + naam. Bij een niet-opgeslagen tekening is `DWGPREFIX` de standaardmap, in accoreconsole of een alleen-lezen map kan `open` `nil` geven; dan crasht `write-line` op `nil`. Er is geen controle op `nil`. Verbeterpunt. | open punt |
| 5 | `(410 . "Model")` | Beperkt alles tot modelspace; entiteiten in paper space/layouts worden niet gezien. Bewust, maar documenteer het. Bij `ssget "X"` in accoreconsole werkt 410 zoals in AutoCAD ⚠️ niet getest. | bewuste beperking |
| 6 | Bowtie-oppervlakte | De shoelace-som heft bij een zelfdoorsnijdende contour (00.06) bijna op: 0,01 m2 en dus geen waarschuwing. LISP detecteert dit niet (bewust, zie python-ezdxf: `is_valid`). | bewuste beperking |
| 7 | `Polyline.Area` (.NET) bij zelfsnijding | Onbekend wat AutoCAD geeft. | ⚠️ niet getest |
| 8 | Bulges (groep 42) | Genegeerd: gebogen wand krijgt de koordenoppervlakte (24,00 i.p.v. 26,80 m2 in `testdata/bulge-demo.dxf`, `uitvoer/ezdxf-bulge-kruiscontrole.txt`). | bekende beperking |
| 9 | Alleen LWPOLYLINE | Oude 2D POLYLINE wordt niet gezien. | bekende beperking |
| 10 | Overlap tussen ruimten | Niet gecontroleerd, bewust. Python + shapely doet dat goedkoop. | bewust niet |
