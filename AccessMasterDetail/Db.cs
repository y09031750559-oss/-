using System.Data;
using System.Data.OleDb;
using System.Reflection;

namespace AccessMasterDetail;

/// <summary>Работа с базой Access (Shop.accdb): создание, загрузка, сохранение.</summary>
internal static class Db
{
    public const string RelationName = "FK_Clients_Orders";

    public static readonly string DbPath = Path.Combine(AppContext.BaseDirectory, "Shop.accdb");

    public static string ConnectionString =>
        $"Provider=Microsoft.ACE.OLEDB.12.0;Data Source={DbPath};Persist Security Info=False;";

    /// <summary>Создаёт файл базы с таблицами и тестовыми данными, если его ещё нет.</summary>
    public static void EnsureDatabase()
    {
        if (File.Exists(DbPath)) return;

        // Пустой .accdb создаём через ADOX (COM), таблицы — через SQL DDL.
        Type catalogType = Type.GetTypeFromProgID("ADOX.Catalog")
            ?? throw new InvalidOperationException("ADOX.Catalog не найден.");
        object catalog = Activator.CreateInstance(catalogType);
        object conn = catalogType.InvokeMember("Create", BindingFlags.InvokeMethod, null, catalog,
            new object[] { ConnectionString });
        conn.GetType().InvokeMember("Close", BindingFlags.InvokeMethod, null, conn, null);
        System.Runtime.InteropServices.Marshal.FinalReleaseComObject(conn);
        System.Runtime.InteropServices.Marshal.FinalReleaseComObject(catalog);

        using var c = new OleDbConnection(ConnectionString);
        c.Open();
        Exec(c, @"CREATE TABLE Clients (
                    ID COUNTER PRIMARY KEY,
                    FullName TEXT(100) NOT NULL,
                    Phone TEXT(30),
                    City TEXT(50))");
        Exec(c, @"CREATE TABLE Orders (
                    ID COUNTER PRIMARY KEY,
                    ClientID INTEGER NOT NULL,
                    OrderDate DATETIME,
                    Product TEXT(100),
                    Quantity INTEGER,
                    Price CURRENCY,
                    CONSTRAINT FK_Orders_Clients FOREIGN KEY (ClientID) REFERENCES Clients (ID))");

        Exec(c, "INSERT INTO Clients (FullName, Phone, City) VALUES ('Иванов Иван', '+7 900 111-11-11', 'Москва')");
        Exec(c, "INSERT INTO Clients (FullName, Phone, City) VALUES ('Петров Пётр', '+7 900 222-22-22', 'Казань')");
        Exec(c, "INSERT INTO Clients (FullName, Phone, City) VALUES ('Сидорова Анна', '+7 900 333-33-33', 'Самара')");

        Exec(c, "INSERT INTO Orders (ClientID, OrderDate, Product, Quantity, Price) VALUES (1, #2026-10-01#, 'Ноутбук', 1, 65000)");
        Exec(c, "INSERT INTO Orders (ClientID, OrderDate, Product, Quantity, Price) VALUES (1, #2026-10-05#, 'Мышь', 2, 900)");
        Exec(c, "INSERT INTO Orders (ClientID, OrderDate, Product, Quantity, Price) VALUES (2, #2026-10-10#, 'Монитор', 1, 18000)");
        Exec(c, "INSERT INTO Orders (ClientID, OrderDate, Product, Quantity, Price) VALUES (3, #2026-10-12#, 'Клавиатура', 1, 2500)");
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
