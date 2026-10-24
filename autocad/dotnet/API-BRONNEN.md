# API-bronnen RcsCheck (.NET)

> ⚠️ Niet gecompileerd op deze Mac. Alleen de API-NAMEN zijn gecontroleerd (bestaan in de XML-documentatie), niet de handtekeningen, overloads of het gedrag.

Bron van de controle: `uitvoer/api-check-nuget-xml.txt`. Methode: nupkg `AutoCAD.NET.Core` 25.0.0 en `AutoCAD.NET.Model` 25.0.0 gedownload van `https://api.nuget.org/v3-flatcontainer/autocad.net.{core,model}/25.0.0/...nupkg` (gezien 24-10-2026) en de XML-docs doorzocht: `AcCoreMgd.xml` (uit Core) en `AcDbMgd.xml` (uit Model). Core 25.0.0 heeft in de nuspec een dependency op `AutoCAD.NET.Model [25.0.0]`.

| # | API-naam | Gevonden in |
|---|---|---|
| 1 | `T:Autodesk.AutoCAD.Runtime.CommandMethodAttribute` | AcCoreMgd.xml |
| 2 | `T:Autodesk.AutoCAD.DatabaseServices.LayerTable` | AcDbMgd.xml |
| 3 | `T:Autodesk.AutoCAD.DatabaseServices.LayerTableRecord` | AcDbMgd.xml |
| 4 | `T:Autodesk.AutoCAD.DatabaseServices.BlockTableRecord` | AcDbMgd.xml |
| 5 | `T:Autodesk.AutoCAD.DatabaseServices.Polyline` | AcDbMgd.xml |
| 6 | `P:Autodesk.AutoCAD.DatabaseServices.Curve.Area` | AcDbMgd.xml |
| 7 | `P:Autodesk.AutoCAD.ApplicationServices.Core.Application.DocumentManager` | AcCoreMgd.xml |
| 8 | `M:Autodesk.AutoCAD.EditorInput.Editor.WriteMessage(System.String)` | AcCoreMgd.xml |
| 9 | `M:Autodesk.AutoCAD.DatabaseServices.TransactionManager.StartTransaction` | AcDbMgd.xml |
| 10 | `M:Autodesk.AutoCAD.DatabaseServices.Transaction.Commit` | AcDbMgd.xml |
| 11 | `T:Autodesk.AutoCAD.DatabaseServices.DBText` | AcDbMgd.xml |
| 12 | `P:Autodesk.AutoCAD.DatabaseServices.Polyline.Closed` | AcDbMgd.xml |
| 13 | `M:Autodesk.AutoCAD.DatabaseServices.SymbolUtilityServices.GetBlockModelSpaceId` | AcDbMgd.xml |
| 14 | `P:Autodesk.AutoCAD.DatabaseServices.Polyline.NumberOfVertices` | AcDbMgd.xml |
| 15 | `M:Autodesk.AutoCAD.DatabaseServices.Polyline.GetPoint2dAt` | AcDbMgd.xml |
| 16 | `M:Autodesk.AutoCAD.DatabaseServices.Polyline.GetBulgeAt` | AcDbMgd.xml |
| 17 | `P:Autodesk.AutoCAD.DatabaseServices.Entity.Layer` | AcDbMgd.xml |
| 18 | `P:Autodesk.AutoCAD.DatabaseServices.DBText.TextString` | AcDbMgd.xml |
| 19 | `P:Autodesk.AutoCAD.DatabaseServices.DBText.Position` | AcDbMgd.xml |
| 20 | `P:Autodesk.AutoCAD.DatabaseServices.Database.LayerTableId` | AcDbMgd.xml |
| 21 | `T:Autodesk.AutoCAD.DatabaseServices.BlockReference` | AcDbMgd.xml |
| 22 | `P:Autodesk.AutoCAD.DatabaseServices.DBObject.Handle` | AcDbMgd.xml |
| 23 | `P:Autodesk.AutoCAD.ApplicationServices.Document.Editor` | AcCoreMgd.xml |
| 24 | `P:Autodesk.AutoCAD.ApplicationServices.Document.Database` | AcCoreMgd.xml |
| 25 | `P:Autodesk.AutoCAD.ApplicationServices.DocumentCollection.MdiActiveDocument` | AcCoreMgd.xml |
| 26 | `P:Autodesk.AutoCAD.DatabaseServices.SymbolTableRecord.Name` | AcDbMgd.xml |
| 27 | `P:Autodesk.AutoCAD.DatabaseServices.Database.Filename` | AcDbMgd.xml |

## Opmerkingen
- `Polyline.Area` staat niet apart in de XML: het is `Curve.Area`, geërfd (rij `P:...Curve.Area`). Dat Polyline van Curve erft is kennis van het objectmodel, ⚠️ niet apart uit de XML gecontroleerd.
- ⚠️ Of `Area` bij een zichzelf snijdende polyline (bowtie 00.06) een bruikbare waarde geeft, is onbekend en niet getest.
- Pakketkeuze Core (AcCoreMgd.dll) en niet `AutoCAD.NET` (AcMgd.dll): het AcMgd-pakket laat accoreconsole en Design Automation crashen (0xC0000005); `Editor.WriteMessage` i.p.v. `Console.WriteLine`; nooit een exception uit een `[CommandMethod]`. Bron: github.com/autodesk-platform-services/aps-lisp-dotnet-skill, `skill/SKILL.md` (versietabel r.44-53; Core r.125; Core.Application r.350; WriteMessage r.352) en `SPEC.md`/`CLAUDE.md` (gezien 24-10-2026; Autodesk-org sample, preview).
- csproj-patroon: `FlangeDA.csproj` in dezelfde repo. Versies uit `feiten-rvb-autocad.md`: 25.0.0 = AutoCAD 2025, net8.0; 25.1.1 = 2026, nuspec toont net10.0 ⚠️ (niet door Autodesk-docs bevestigd). Dit project mikt op 25.0.0 / net8.0-windows.
- `PackageContents.xml`: patroon `dotnet-outputs/FlangeDA/PackageContents.xml`; ⚠️ niet getest als bundle.
