using System;
using System.Collections.Generic;
using System.IO;

namespace RvbPostgis.Core
{
    /// <summary>
    /// Verbinding en laagnaam komen NIET uit de tekening (RCS: geen databasekoppelingen in dwg),
    /// maar uit omgevingsvariabele RVB_PG_CONNECTION of uit rvbpostgis.conf naast de plugin-DLL.
    /// </summary>
    public static class Instellingen
    {
        public const string EnvVerbinding = "RVB_PG_CONNECTION";
        public const string Bestandsnaam = "rvbpostgis.conf";
        public const string StandaardLaag = "92 Rust- en werkgebieden";

        /// <summary>Regels "sleutel=waarde"; lege regels en regels die met # beginnen worden overgeslagen.</summary>
        public static Dictionary<string, string> Parse(IEnumerable<string> regels)
        {
            var d = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            foreach (var r in regels)
            {
                var t = r.Trim();
                if (t.Length == 0 || t.StartsWith("#")) continue;
                int i = t.IndexOf('=');
                if (i <= 0) continue;
                d[t.Substring(0, i).Trim()] = t.Substring(i + 1).Trim();
            }
            return d;
        }

        /// <summary>Omgevingsvariabele wint van het bestand. Null als er niets is ingesteld.</summary>
        public static string Verbinding(string envWaarde, IDictionary<string, string> bestand)
        {
            if (!string.IsNullOrWhiteSpace(envWaarde)) return envWaarde;
            string v;
            if (bestand != null && bestand.TryGetValue("ConnectionString", out v) && !string.IsNullOrWhiteSpace(v)) return v;
            return null;
        }

        public static string Laag(IDictionary<string, string> bestand)
        {
            string v;
            if (bestand != null && bestand.TryGetValue("Laag", out v) && !string.IsNullOrWhiteSpace(v)) return v;
            return StandaardLaag;
        }

        public static Dictionary<string, string> LeesBestand(string map)
        {
            var pad = Path.Combine(map, Bestandsnaam);
            return File.Exists(pad) ? Parse(File.ReadAllLines(pad)) : new Dictionary<string, string>();
        }
    }
}
