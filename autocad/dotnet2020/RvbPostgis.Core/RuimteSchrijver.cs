using System;
using System.Collections.Generic;
using Npgsql;
using NpgsqlTypes;

namespace RvbPostgis.Core
{
    public static class RuimteSchrijver
    {
        /// <summary>Alles of niets: één transactie, parameters per rij. Geeft het aantal geschreven rijen.</summary>
        public static int Schrijf(string verbinding, string tekening, IEnumerable<RuimteContour> ruimten)
        {
            int n = 0;
            using (var bron = NpgsqlDataSource.Create(verbinding))
            using (var conn = bron.OpenConnection())
            using (var tx = conn.BeginTransaction())
            {
                foreach (var r in ruimten)
                {
                    using (var cmd = new NpgsqlCommand(RuimteSql.Insert, conn, tx))
                    {
                        cmd.Parameters.Add(new NpgsqlParameter { NpgsqlDbType = NpgsqlDbType.Text, Value = tekening });
                        cmd.Parameters.Add(new NpgsqlParameter { NpgsqlDbType = NpgsqlDbType.Text, Value = r.Handle });
                        cmd.Parameters.Add(new NpgsqlParameter { NpgsqlDbType = NpgsqlDbType.Text, Value = r.Laag });
                        cmd.Parameters.Add(new NpgsqlParameter { NpgsqlDbType = NpgsqlDbType.Text, Value = (object)r.Ruimtenummer ?? DBNull.Value });
                        cmd.Parameters.Add(new NpgsqlParameter { NpgsqlDbType = NpgsqlDbType.Text, Value = RuimteLogica.NaarWkt(r.Punten) });
                        n += cmd.ExecuteNonQuery();
                    }
                }
                tx.Commit();   // zonder Commit rolt Dispose alles terug
            }
            return n;
        }
    }
}
