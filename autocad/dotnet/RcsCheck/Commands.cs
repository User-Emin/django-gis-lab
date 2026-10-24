// ⚠️ Niet gecompileerd op deze Mac en niet in AutoCAD uitgevoerd.
// RCSCHECK in C#: dezelfde regels als lisp/rcs-check.lsp en python-ezdxf/rcs_check.py (de referentie).
// Verschil met LISP: Polyline.Area (geërfd van Curve.Area) neemt bulges wel mee.
// API-namen gecontroleerd in de XML-docs van AutoCAD.NET.Core/Model 25.0.0: zie ../API-BRONNEN.md.
using System.Text.RegularExpressions;
using Autodesk.AutoCAD.ApplicationServices.Core;   // Core.Application, niet de desktop-Application (AcMgd)
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;

[assembly: CommandClass(typeof(RcsCheck.Commands))]

namespace RcsCheck;

public class Commands
{
    const string RuimteLaag = "92 Rust- en werkgebieden";
    static readonly Regex LaagRe = new(@"^[0-9]{2} [A-Za-z0-9 _-]+$");
    static readonly Regex NrRe = new(@"^[0-9]{2}\.[0-9]{2}$");

    [CommandMethod("RCSCHECK")]
    public void RcsCheck()
    {
        var doc = Application.DocumentManager.MdiActiveDocument;
        Editor ed = doc.Editor;
        Database db = doc.Database;
        int fouten = 0;
        try
        {
            using Transaction tr = db.TransactionManager.StartTransaction();
            var ms = (BlockTableRecord)tr.GetObject(SymbolUtilityServices.GetBlockModelSpaceId(db), OpenMode.ForRead);

            // modelspace één keer doorlopen: tellen per laag, laag 0, nummers en ruimtecontouren
            var perLaag = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
            var nummers = new List<(string Nr, double X, double Y)>();
            var ruimten = new List<Polyline>();
            ed.WriteMessage("\nRCSCHECK (.NET)\n-- Laag 0 --");
            foreach (ObjectId id in ms)
            {
                var ent = (Entity)tr.GetObject(id, OpenMode.ForRead);
                perLaag[ent.Layer] = perLaag.GetValueOrDefault(ent.Layer) + 1;
                if (ent.Layer == "0" && ent is not BlockReference)
                {
                    ed.WriteMessage($"\nFOUT laag 0 bevat {ent.GetRXClass().DxfName} (handle {ent.Handle})");
                    fouten++;
                }
                if (ent.Layer == RuimteLaag && ent is DBText t && NrRe.IsMatch(t.TextString))
                    nummers.Add((t.TextString, t.Position.X, t.Position.Y));   // Position = groep 10
                if (ent.Layer == RuimteLaag && ent is Polyline pl)
                    ruimten.Add(pl);
            }

            ed.WriteMessage("\n-- Laagnamen en lege lagen --");
            var lt = (LayerTable)tr.GetObject(db.LayerTableId, OpenMode.ForRead);
            foreach (ObjectId id in lt)
            {
                var ltr = (LayerTableRecord)tr.GetObject(id, OpenMode.ForRead);
                string naam = ltr.Name;
                if (naam == "0" || naam.Equals("Defpoints", StringComparison.OrdinalIgnoreCase)) continue;
                if (!LaagRe.IsMatch(naam)) { ed.WriteMessage($"\nFOUT laagnaam: '{naam}' voldoet niet aan '## omschrijving'"); fouten++; }
                if (perLaag.GetValueOrDefault(naam) == 0) { ed.WriteMessage($"\nFOUT lege laag: '{naam}'"); fouten++; }
            }

            ed.WriteMessage("\n-- Ruimtelijst (laag 92) --\nnummer;handle;gesloten;opp_m2");
            foreach (Polyline pl in ruimten)
            {
                var pts = Enumerable.Range(0, pl.NumberOfVertices).Select(i => pl.GetPoint2dAt(i)).ToList();
                var gev = nummers.Where(n => Binnen(n.X, n.Y, pts)).Select(n => n.Nr).ToList();
                string nr = gev.Count == 1 ? gev[0] : gev.Count == 0 ? "?" : "meerdere";
                if (gev.Count != 1) { ed.WriteMessage($"\nFOUT ruimte {pl.Handle}: {gev.Count} ruimtenummers in contour"); fouten++; }
                string opp = "";
                if (pl.Closed) opp = (pl.Area / 1e6).ToString("F2", System.Globalization.CultureInfo.InvariantCulture);
                else { ed.WriteMessage($"\nFOUT ruimte {pl.Handle} ({nr}): polyline niet gesloten"); fouten++; }
                ed.WriteMessage($"\n{nr};{pl.Handle};{(pl.Closed ? "ja" : "nee")};{opp}");
            }
            ed.WriteMessage($"\nKlaar: {fouten} bevinding(en).\n");
            tr.Commit();   // alleen gelezen, maar Commit is goedkoper dan Abort en het vaste patroon
        }
        catch (System.Exception ex)
        {
            // nooit een exception uit een [CommandMethod] laten ontsnappen (aps-lisp-dotnet-skill SKILL.md)
            ed.WriteMessage($"\nERROR: {ex.Message}\n");
        }
    }

    // ray casting, zelfde als binnen() in rcs_check.py
    static bool Binnen(double x, double y, List<Autodesk.AutoCAD.Geometry.Point2d> p)
    {
        bool res = false;
        for (int i = 0, j = p.Count - 1; i < p.Count; j = i++)
            if ((p[i].Y > y) != (p[j].Y > y) && x < (p[j].X - p[i].X) * (y - p[i].Y) / (p[j].Y - p[i].Y) + p[i].X)
                res = !res;
        return res;
    }
}
