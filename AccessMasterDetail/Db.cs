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
            if (Offline)
                LoadOffline(ds);
            else
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
                id.AutoIncrementSeed = Offline ? NextId(t) : -1;
                id.AutoIncrementStep = Offline ? 1 : -1;
                id.ReadOnly = false; // чтобы после сохранения можно было записать настоящий ID
            }

            orders.Columns["OrderDate"].DefaultValue = DateTime.Today;
            orders.Columns["Quantity"].DefaultValue = 1;
            orders.Columns["Price"].DefaultValue = 0m;

            // Связь: при удалении/смене ID клиента изменения каскадно идут в заказы.
            ds.Relations.Add(RelationName, clients.Columns["ID"], orders.Columns["ClientID"]);
            return ds;
        }

        /// <summary>Резервный режим: если драйвер Access недоступен, данные хранятся в Shop.xml.</summary>
        public static bool Offline;
        public static readonly string XmlPath = Path.Combine(AppContext.BaseDirectory, "Shop.xml");

        private static int NextId(DataTable t)
        {
            int max = 0;
            foreach (DataRow r in t.Rows) if (r["ID"] is int i && i > max) max = i;
            return max + 1;
        }

        private static void LoadOffline(DataSet ds)
        {
            var clients = ds.Tables.Add("Clients");
            clients.Columns.Add("ID", typeof(int));
            clients.Columns.Add("FullName", typeof(string));
            clients.Columns.Add("Phone", typeof(string));
            clients.Columns.Add("City", typeof(string));
            clients.PrimaryKey = new[] { clients.Columns["ID"] };

            var orders = ds.Tables.Add("Orders");
            orders.Columns.Add("ID", typeof(int));
            orders.Columns.Add("ClientID", typeof(int));
            orders.Columns.Add("OrderDate", typeof(DateTime));
            orders.Columns.Add("Product", typeof(string));
            orders.Columns.Add("Quantity", typeof(int));
            orders.Columns.Add("Price", typeof(decimal));
            orders.PrimaryKey = new[] { orders.Columns["ID"] };

            if (File.Exists(XmlPath))
            {
                try { ds.ReadXml(XmlPath, XmlReadMode.IgnoreSchema); ds.AcceptChanges(); return; }
                catch { ds.Clear(); }
            }
            clients.Rows.Add(1, "Иванов Иван", "+7 900 111-11-11", "Москва");
            clients.Rows.Add(2, "Петров Пётр", "+7 900 222-22-22", "Казань");
            clients.Rows.Add(3, "Сидорова Анна", "+7 900 333-33-33", "Самара");
            orders.Rows.Add(1, 1, new DateTime(2026, 10, 1), "Ноутбук", 1, 65000m);
            orders.Rows.Add(2, 1, new DateTime(2026, 10, 5), "Мышь", 2, 900m);
            orders.Rows.Add(3, 2, new DateTime(2026, 10, 10), "Монитор", 1, 18000m);
            orders.Rows.Add(4, 3, new DateTime(2026, 10, 12), "Клавиатура", 1, 2500m);
            ds.AcceptChanges();
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
            if (Offline)
            {
                ds.WriteXml(XmlPath);
                return;
            }

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
