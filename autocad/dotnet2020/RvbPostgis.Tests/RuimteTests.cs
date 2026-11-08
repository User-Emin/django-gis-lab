using System.Collections.Generic;
using System.Linq;
using Npgsql;
using RvbPostgis.Core;
using Xunit;

namespace RvbPostgis.Tests
{
    public class RuimteTests
    {
        static List<Punt> Vierkant(double x0 = 120000, double y0 = 487000, double z = 10)
        {
            return new List<Punt> { new Punt(x0, y0), new Punt(x0 + z, y0), new Punt(x0 + z, y0 + z), new Punt(x0, y0 + z) };
        }

        static RuimteContour Contour(List<Punt> p, bool gesloten = true, bool bogen = false)
        {
            return new RuimteContour { Handle = "2A", Laag = "92 Rust- en werkgebieden", Punten = p, IsGesloten = gesloten, HeeftBogen = bogen };
        }

        [Fact]
        public void Wkt_sluit_de_ring_en_gebruikt_punt_als_decimaalteken()
        {
            var wkt = RuimteLogica.NaarWkt(new List<Punt> { new Punt(0.5, 0), new Punt(10, 0), new Punt(10, 5.25) });
            Assert.Equal("POLYGON((0.5 0, 10 0, 10 5.25, 0.5 0))", wkt);
        }

        [Fact]
        public void Wkt_herhaalt_het_eerste_punt_niet_dubbel()
        {
            var p = Vierkant(); p.Add(p[0]);
            Assert.EndsWith("120000 487000))", RuimteLogica.NaarWkt(p));
            Assert.Equal(2, RuimteLogica.NaarWkt(p).Split(new[] { "120000 487000" }, System.StringSplitOptions.None).Length - 1);
        }

        [Fact] public void Gesloten_vierkant_is_geldig() { Assert.Null(RuimteLogica.Valideer(Contour(Vierkant()))); }

        [Fact] public void Open_polylijn_wordt_afgekeurd() { Assert.Contains("niet gesloten", RuimteLogica.Valideer(Contour(Vierkant(), gesloten: false))); }

        [Fact] public void Bogen_worden_afgekeurd() { Assert.Contains("bogen", RuimteLogica.Valideer(Contour(Vierkant(), bogen: true))); }

        [Fact]
        public void Minder_dan_drie_punten_wordt_afgekeurd()
        {
            Assert.Contains("minder dan 3", RuimteLogica.Valideer(Contour(Vierkant().Take(2).ToList())));
        }

        [Fact]
        public void Lokale_coordinaten_vallen_buiten_RD()
        {
            Assert.Contains("RD-bereik", RuimteLogica.Valideer(Contour(Vierkant(0, 0))));
            Assert.Null(RuimteLogica.Valideer(Contour(Vierkant(0, 0)), controleerRd: false));
        }

        [Fact]
        public void Oppervlak_en_punt_in_polygoon()
        {
            var v = Vierkant();
            Assert.Equal(100, System.Math.Abs(RuimteLogica.Oppervlak(v)), 6);
            Assert.True(RuimteLogica.PuntInPolygoon(new Punt(120005, 487005), v));
            Assert.False(RuimteLogica.PuntInPolygoon(new Punt(120011, 487005), v));
        }

        [Fact]
        public void Ruimtenummer_en_laagfilter()
        {
            Assert.True(RuimteLogica.IsRuimtenummer(" 01.12 "));
            Assert.False(RuimteLogica.IsRuimtenummer("1.2"));
            Assert.True(RuimteLogica.LaagMatcht("92 RUST- EN WERKGEBIEDEN", Instellingen.StandaardLaag));
        }

        [Fact]
        public void Instellingen_omgevingsvariabele_wint_van_bestand()
        {
            var conf = Instellingen.Parse(new[] { "# commentaar", "", "ConnectionString = Host=bestand", "Laag=X" });
            Assert.Equal("Host=bestand", Instellingen.Verbinding(null, conf));
            Assert.Equal("Host=env", Instellingen.Verbinding("Host=env", conf));
            Assert.Null(Instellingen.Verbinding("  ", new Dictionary<string, string>()));
            Assert.Equal("X", Instellingen.Laag(conf));
            Assert.Equal(Instellingen.StandaardLaag, Instellingen.Laag(new Dictionary<string, string>()));
        }

        [Fact]
        public void Insert_gebruikt_alleen_parameters()
        {
            for (int i = 1; i <= RuimteSql.AantalParameters; i++) Assert.Contains("$" + i, RuimteSql.Insert);
            Assert.DoesNotContain("'", RuimteSql.Insert);
            Assert.Contains("ST_GeomFromText($5, 28992)", RuimteSql.Insert);
        }

        [Fact]
        public void Npgsql_met_NetTopologySuite_laadt_op_net47()
        {
            // Meting voor les 35: restore + laden van Npgsql.NetTopologySuite 8.0.9 op net47 (geen databaseverbinding).
            var b = new NpgsqlDataSourceBuilder("Host=127.0.0.1;Database=x");
            b.UseNetTopologySuite();
            using (var bron = b.Build()) Assert.NotNull(bron);
        }
    }
}
