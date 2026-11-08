namespace RvbPostgis.Core
{
    /// <summary>SQL-tekst als constanten. Waarden gaan ALTIJD als parameters ($1..$5), nooit als tekst in de SQL.</summary>
    public static class RuimteSql
    {
        public const string Insert =
            "INSERT INTO cad_ruimte_import (tekening, handle, laag, ruimtenummer, geom) " +
            "VALUES ($1, $2, $3, $4, ST_GeomFromText($5, 28992)) " +
            "ON CONFLICT (tekening, handle) DO UPDATE SET " +
            "laag = EXCLUDED.laag, ruimtenummer = EXCLUDED.ruimtenummer, " +
            "geom = EXCLUDED.geom, geimporteerd_op = now()";

        public const int AantalParameters = 5;
    }
}
