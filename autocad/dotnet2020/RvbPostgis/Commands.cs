// ⚠️ Gebouwd in CI, NIET in AutoCAD uitgevoerd. API-namen: AutoCAD.NET 23.1.0 (AutoCAD 2020).
using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;
using RvbPostgis.Core;

[assembly: CommandClass(typeof(RvbPostgis.Commands))]

namespace RvbPostgis
{
    public class Commands
    {
        [CommandMethod("RVBNAARPOSTGIS")]
        public void NaarPostgis()
        {
            Document doc = Application.DocumentManager.MdiActiveDocument;
            Editor ed = doc.Editor;
            try
            {
                string map = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
                var conf = Instellingen.LeesBestand(map);
                string verbinding = Instellingen.Verbinding(Environment.GetEnvironmentVariable(Instellingen.EnvVerbinding), conf);
                if (verbinding == null)
                {
                    ed.WriteMessage("\nGeen verbinding: zet RVB_PG_CONNECTION of ConnectionString in " + Instellingen.Bestandsnaam + " naast de DLL.");
                    return;
                }
                string laag = Instellingen.Laag(conf);

                // Selectiefilter: gesloten-of-niet maakt AutoCAD niet uit; de laag wel. Tekst op dezelfde laag levert het ruimtenummer.
                var filter = new SelectionFilter(new[]
                {
                    new TypedValue((int)DxfCode.Operator, "<OR"),
                      new TypedValue((int)DxfCode.Start, "LWPOLYLINE"),
                      new TypedValue((int)DxfCode.Start, "TEXT"),
                    new TypedValue((int)DxfCode.Operator, "OR>"),
                    new TypedValue((int)DxfCode.LayerName, laag)
                });
                PromptSelectionResult sel = ed.GetSelection(filter);
                if (sel.Status != PromptStatus.OK) return;

                var ruimten = new List<RuimteContour>();
                var nummers = new List<KeyValuePair<Punt, string>>();
                int afgekeurd = 0;

                using (Transaction tr = doc.Database.TransactionManager.StartTransaction())
                {
                    foreach (SelectedObject so in sel.Value)
                    {
                        var ent = tr.GetObject(so.ObjectId, OpenMode.ForRead) as Entity;
                        if (ent == null || !RuimteLogica.LaagMatcht(ent.Layer, laag)) continue;

                        var pl = ent as Polyline;
                        if (pl != null)
                        {
                            var punten = new List<Punt>();
                            bool bogen = false;
                            for (int i = 0; i < pl.NumberOfVertices; i++)
                            {
                                var p = pl.GetPoint2dAt(i);
                                punten.Add(new Punt(p.X, p.Y));
                                if (Math.Abs(pl.GetBulgeAt(i)) > 1e-12) bogen = true;
                            }
                            var c = new RuimteContour { Handle = pl.Handle.ToString(), Laag = pl.Layer, Punten = punten, IsGesloten = pl.Closed, HeeftBogen = bogen };
                            string reden = RuimteLogica.Valideer(c);
                            if (reden != null) { ed.WriteMessage("\nOvergeslagen " + c.Handle + ": " + reden); afgekeurd++; }
                            else ruimten.Add(c);
                            continue;
                        }
                        var t = ent as DBText;
                        if (t != null && RuimteLogica.IsRuimtenummer(t.TextString))
                            nummers.Add(new KeyValuePair<Punt, string>(new Punt(t.Position.X, t.Position.Y), t.TextString.Trim()));
                    }
                    tr.Commit();
                }

                foreach (var r in ruimten)
                    foreach (var n in nummers)
                        if (RuimteLogica.PuntInPolygoon(n.Key, r.Punten)) { r.Ruimtenummer = n.Value; break; }

                if (ruimten.Count == 0) { ed.WriteMessage("\nGeen bruikbare ruimten (" + afgekeurd + " afgekeurd)."); return; }

                string tekening = Path.GetFileName(doc.Name);
                int geschreven = RuimteSchrijver.Schrijf(verbinding, tekening, ruimten);
                ed.WriteMessage("\n" + geschreven + " ruimte(n) naar PostGIS, " + afgekeurd + " overgeslagen.");
            }
            catch (System.Exception ex)
            {
                // Geen verbindingsstring in de melding: ex.Message van Npgsql bevat die normaal niet, maar we tonen alleen het type en de boodschap.
                ed.WriteMessage("\nRVBNAARPOSTGIS mislukt: " + ex.GetType().Name + ": " + ex.Message);
            }
        }
    }
}
