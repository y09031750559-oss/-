using System;
using System.Data;
using System.Data.OleDb;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Windows.Forms;

namespace AccessMasterDetail
{
    /// <summary>Работа с базой Access (Shop.accdb): создание, загрузка, сохранение.</summary>
    internal static class Db
    {
        public const string RelationName = "FK_Clients_Orders";

        // Драйверы Access: ACE из Office или встроенный в Windows Jet 4.0.
        private static readonly string[] Providers =
            { "Microsoft.ACE.OLEDB.16.0", "Microsoft.ACE.OLEDB.12.0", "Microsoft.Jet.OLEDB.4.0" };

        private static string Provider = Providers[0];

        // База Access (формат .mdb, открывается в Access). Готовый файл вшит в программу.
        public static readonly string DbPath = Path.Combine(AppContext.BaseDirectory, "Shop.mdb");

        public static string ConnectionString => $"Provider={Provider};Data Source={DbPath}";

        /// <summary>Выкладывает файл базы рядом с программой (если его нет) и подбирает рабочий драйвер.</summary>
        public static void EnsureDatabase()
        {
            if (!File.Exists(DbPath))
            {
                using (var res = Assembly.GetExecutingAssembly().GetManifestResourceStream("Shop.mdb"))
                using (var file = File.Create(DbPath))
                    res.CopyTo(file);
            }

            var errors = new System.Text.StringBuilder();
            foreach (var p in Providers)
            {
                Provider = p;
                try
                {
                    using (var c = new OleDbConnection(ConnectionString)) c.Open();
                    return;
                }
                catch (Exception ex) { errors.AppendLine(p + ": " + ex.Message); }
            }
            throw new InvalidOperationException(errors.ToString());
        }

        private static void Exec(OleDbConnection c, string sql)
        {
            using var cmd = new OleDbCommand(sql, c);
            cmd.ExecuteNonQuery();
        }

        /// <summary>Загружает обе таблицы в DataSet и связывает их отношением главная → подчинённая.</summary>
        public static DataSet Load()
        {
            var ds = new DataSet("Shop");
            using (var c = new OleDbConnection(ConnectionString))
            {
                Fill(c, ds, "Clients");
                Fill(c, ds, "Orders");
            }

            var clients = ds.Tables["Clients"];
            var orders = ds.Tables["Orders"];

            // Локальные ID новых строк — отрицательные, чтобы не пересекаться с настоящими.
            foreach (var t in new[] { clients, orders })
            {
                var id = t.Columns["ID"];
                id.AutoIncrement = true;
                id.AutoIncrementSeed = -1;
                id.AutoIncrementStep = -1;
                id.ReadOnly = false; // чтобы после сохранения можно было записать настоящий ID
            }

            orders.Columns["OrderDate"].DefaultValue = DateTime.Today;
            orders.Columns["Quantity"].DefaultValue = 1;
            orders.Columns["Price"].DefaultValue = 0m;

            // Связь: при удалении/смене ID клиента изменения каскадно идут в заказы.
            ds.Relations.Add(RelationName, clients.Columns["ID"], orders.Columns["ClientID"]);
            return ds;
        }

        private static void Fill(OleDbConnection c, DataSet ds, string table)
        {
            using var da = new OleDbDataAdapter($"SELECT * FROM [{table}]", c);
            da.FillSchema(ds, SchemaType.Source, table);
            da.Fill(ds, table);
        }

        /// <summary>Сохраняет изменения в правильном порядке (сначала главная, потом подчинённая).</summary>
        public static void Save(DataSet ds)
        {
            var clients = ds.Tables["Clients"];
            var orders = ds.Tables["Orders"];

            using var c = new OleDbConnection(ConnectionString);
            c.Open();
            using var tr = c.BeginTransaction();
            try
            {
                var daClients = CreateAdapter(c, tr, "Clients");
                var daOrders = CreateAdapter(c, tr, "Orders");

                // 1. Удалённые заказы  2. Новые/изменённые клиенты  3. Новые/изменённые заказы  4. Удалённые клиенты
                daOrders.Update(orders.Select(null, null, DataViewRowState.Deleted));
                daClients.Update(clients.Select(null, null, DataViewRowState.Added | DataViewRowState.ModifiedCurrent));
                daOrders.Update(orders.Select(null, null, DataViewRowState.Added | DataViewRowState.ModifiedCurrent));
                daClients.Update(clients.Select(null, null, DataViewRowState.Deleted));

                tr.Commit();
            }
            catch
            {
                tr.Rollback();
                throw;
            }
        }

        private static OleDbDataAdapter CreateAdapter(OleDbConnection c, OleDbTransaction tr, string table)
        {
            var da = new OleDbDataAdapter(new OleDbCommand($"SELECT * FROM [{table}]", c, tr));
            var cb = new OleDbCommandBuilder(da) { QuotePrefix = "[", QuoteSuffix = "]" };

            da.InsertCommand = cb.GetInsertCommand();
            da.UpdateCommand = cb.GetUpdateCommand();
            da.DeleteCommand = cb.GetDeleteCommand();
            foreach (var cmd in new[] { da.InsertCommand, da.UpdateCommand, da.DeleteCommand })
                cmd.Transaction = tr;

            // После INSERT получаем настоящий ID из Access; через DataRelation он
            // автоматически проставится в ClientID подчинённых заказов.
            da.RowUpdated += (s, e) =>
            {
                if (e.StatementType == StatementType.Insert && e.Status == UpdateStatus.Continue)
                {
                    using var idCmd = new OleDbCommand("SELECT @@IDENTITY", c, tr);
                    var id = Convert.ToInt32(idCmd.ExecuteScalar());
                    e.Row["ID"] = id;
                }
            };
            return da;
        }
    }
}
