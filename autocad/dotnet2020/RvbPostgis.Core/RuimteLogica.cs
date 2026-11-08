using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

namespace RvbPostgis.Core
{
    /// <summary>Een 2D-punt in tekeningcoördinaten (aangenomen: EPSG:28992, meter).</summary>
    public struct Punt
    {
        public readonly double X;
        public readonly double Y;
        public Punt(double x, double y) { X = x; Y = y; }
    }

    /// <summary>Wat het AutoCAD-commando uit één polylijn haalt; geen AutoCAD-types.</summary>
    public sealed class RuimteContour
    {
        public string Handle { get; set; }
        public string Laag { get; set; }
        public IList<Punt> Punten { get; set; }
        public bool IsGesloten { get; set; }
        public bool HeeftBogen { get; set; }
        public string Ruimtenummer { get; set; }
    }

    public static class RuimteLogica
    {
        // Grove plausibiliteit voor RD New (EPSG:28992): eigen keuze, geen EPSG-grens ⚠️.
        // Vangt tekeningen op in lokale coördinaten (RCS: gebouw bij de oorsprong van het WCS).
        public const double RdMinX = 0, RdMaxX = 300000, RdMinY = 300000, RdMaxY = 620000;
        public const int Srid = 28992;
        static readonly Regex NummerRe = new Regex(@"^[0-9]{2}\.[0-9]{2}$");

        /// <summary>Geeft null als de contour bruikbaar is, anders de reden (Nederlands).</summary>
        public static string Valideer(RuimteContour c, bool controleerRd = true)
        {
            if (c == null || c.Punten == null) return "geen contour";
            if (!c.IsGesloten) return "polylijn is niet gesloten";
            if (c.HeeftBogen) return "polylijn bevat bogen (bulge); alleen rechte segmenten ondersteund";
            if (c.Punten.Count < 3) return "minder dan 3 hoekpunten (" + c.Punten.Count + ")";
            if (Math.Abs(Oppervlak(c.Punten)) < 1e-9) return "oppervlak is nul";
            if (controleerRd)
                foreach (var p in c.Punten)
                    if (p.X < RdMinX || p.X > RdMaxX || p.Y < RdMinY || p.Y > RdMaxY)
                        return "punt buiten het RD-bereik (" + F(p.X) + " " + F(p.Y) + "): lokale coördinaten?";
            return null;
        }

        /// <summary>WKT van een gesloten ring; herhaalt het eerste punt als laatste. Punt als scheidingsteken (cultuur-onafhankelijk).</summary>
        public static string NaarWkt(IList<Punt> punten)
        {
            if (punten == null || punten.Count < 3) throw new ArgumentException("minimaal 3 punten");
            var sb = new StringBuilder("POLYGON((");
            for (int i = 0; i < punten.Count; i++)
                sb.Append(i == 0 ? "" : ", ").Append(F(punten[i].X)).Append(' ').Append(F(punten[i].Y));
            var a = punten[0]; var z = punten[punten.Count - 1];
            if (a.X != z.X || a.Y != z.Y)
                sb.Append(", ").Append(F(a.X)).Append(' ').Append(F(a.Y));
            return sb.Append("))").ToString();
        }

        public static double Oppervlak(IList<Punt> p)
        {
            double s = 0;
            for (int i = 0; i < p.Count; i++)
            {
                var a = p[i]; var b = p[(i + 1) % p.Count];
                s += a.X * b.Y - b.X * a.Y;
            }
            return s / 2.0;
        }

        /// <summary>Ray casting; punten op de rand tellen niet gegarandeerd mee.</summary>
        public static bool PuntInPolygoon(Punt q, IList<Punt> p)
        {
            bool binnen = false;
            for (int i = 0, j = p.Count - 1; i < p.Count; j = i++)
                if ((p[i].Y > q.Y) != (p[j].Y > q.Y) &&
                    q.X < (p[j].X - p[i].X) * (q.Y - p[i].Y) / (p[j].Y - p[i].Y) + p[i].X)
                    binnen = !binnen;
            return binnen;
        }

        public static bool IsRuimtenummer(string tekst) { return tekst != null && NummerRe.IsMatch(tekst.Trim()); }

        public static bool LaagMatcht(string laag, string filter)
        {
            return string.Equals(laag, filter, StringComparison.OrdinalIgnoreCase);
        }

        static string F(double v) { return v.ToString("0.###", CultureInfo.InvariantCulture); }
    }
}
