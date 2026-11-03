// Вставьте этот файл целиком вместо содержимого Program.cs
// Нужен NuGet-пакет System.Data.OleDb
#nullable disable
using System;
using System.Data;
using System.Data.OleDb;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Windows.Forms;

namespace AccessMasterDetail
{

    internal static class Program
    {
        [STAThread]
        private static void Main()
        {
            Application.SetHighDpiMode(HighDpiMode.SystemAware);
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            try
            {
                Db.EnsureDatabase();
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    "Не удалось открыть/создать базу Access.\n\n" + ex.Message +
                    "\n\nУстановите Microsoft Access Database Engine (той же разрядности, что и PlatformTarget в .csproj).",
                    "Ошибка", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }
            Application.Run(new MainForm());
        }
    }

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

    /// <summary>Главная форма: список клиентов + встроенная подчинённая таблица заказов.</summary>
    public class MainForm : Form
    {
        private readonly DataSet _ds;
        private readonly BindingSource _clientsBs = new();
        private readonly BindingSource _ordersBs = new();
        private readonly DataGridView _clientsGrid = Grids.Create();
        private readonly DataGridView _ordersGrid = Grids.Create();
        private OrdersForm _ordersForm;

        public MainForm()
        {
            Text = "Клиенты — главная форма (Access)";
            Width = 900;
            Height = 600;
            StartPosition = FormStartPosition.CenterScreen;

            _ds = Db.Load();

            // Главная таблица
            _clientsBs.DataSource = _ds;
            _clientsBs.DataMember = "Clients";
            _clientsGrid.DataSource = _clientsBs;

            // Подчинённая таблица: источник — связь главной BindingSource,
            // поэтому показываются только заказы текущего клиента.
            _ordersBs.DataSource = _clientsBs;
            _ordersBs.DataMember = Db.RelationName;
            _ordersGrid.DataSource = _ordersBs;

            Grids.SetupClients(_clientsGrid);
            Grids.SetupOrders(_ordersGrid);

            var toolbar = new ToolStrip();
            toolbar.Items.Add("Добавить клиента", null, (_, _) => _clientsBs.AddNew());
            toolbar.Items.Add("Удалить клиента", null, (_, _) => DeleteClient());
            toolbar.Items.Add(new ToolStripSeparator());
            toolbar.Items.Add("Открыть подчинённую форму (заказы)", null, (_, _) => OpenOrdersForm());
            toolbar.Items.Add(new ToolStripSeparator());
            toolbar.Items.Add("Сохранить", null, (_, _) => SaveAll());
            toolbar.Items.Add("Обновить", null, (_, _) => Reload());

            var split = new SplitContainer
            {
                Dock = DockStyle.Fill,
                Orientation = Orientation.Horizontal
            };
            Load += (_, _) => split.SplitterDistance = ClientSize.Height / 2 - 20;
            split.Panel1.Controls.Add(_clientsGrid);
            split.Panel1.Controls.Add(Caption("Клиенты (главная таблица)"));
            split.Panel2.Controls.Add(_ordersGrid);
            split.Panel2.Controls.Add(Caption("Заказы выбранного клиента (подчинённая таблица)"));

            Controls.Add(split);
            Controls.Add(toolbar);

            _clientsGrid.CellDoubleClick += (_, _) => OpenOrdersForm();
            FormClosing += OnFormClosing;
        }

        private static Label Caption(string text) => new()
        {
            Text = text,
            Dock = DockStyle.Top,
            Height = 24,
            TextAlign = ContentAlignment.MiddleLeft,
            Font = new Font(SystemFonts.DefaultFont, FontStyle.Bold)
        };

        public BindingSource ClientsBinding => _clientsBs;

        private void OpenOrdersForm()
        {
            if (_clientsBs.Current == null) return;
            if (_ordersForm == null || _ordersForm.IsDisposed)
            {
                _ordersForm = new OrdersForm(this);
                _ordersForm.Show(this);
            }
            else
            {
                _ordersForm.Activate();
            }
        }

        private void DeleteClient()
        {
            if (_clientsBs.Current is not DataRowView row) return;
            var answer = MessageBox.Show(
                $"Удалить клиента «{row["FullName"]}» и все его заказы?",
                "Подтверждение", MessageBoxButtons.YesNo, MessageBoxIcon.Question);
            if (answer == DialogResult.Yes)
                _clientsBs.RemoveCurrent(); // заказы удалятся каскадно через DataRelation
        }

        public bool SaveAll()
        {
            try
            {
                Validate();
                _clientsBs.EndEdit();
                _ordersBs.EndEdit();
                _ordersForm?.EndEdit();

                if (!_ds.HasChanges()) return true;
                Db.Save(_ds);
                _ds.AcceptChanges();
                return true;
            }
            catch (Exception ex)
            {
                MessageBox.Show("Ошибка сохранения:\n" + ex.Message, "Ошибка",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
                return false;
            }
        }

        private void Reload()
        {
            _clientsBs.EndEdit();
            if (_ds.HasChanges() &&
                MessageBox.Show("Есть несохранённые изменения. Отменить их?", "Обновить",
                    MessageBoxButtons.YesNo, MessageBoxIcon.Warning) != DialogResult.Yes)
                return;

            _ds.Clear();
            var fresh = Db.Load();
            _ds.Merge(fresh);
            _ds.AcceptChanges();
        }

        private void OnFormClosing(object sender, FormClosingEventArgs e)
        {
            _clientsBs.EndEdit();
            _ordersBs.EndEdit();
            if (!_ds.HasChanges()) return;

            var answer = MessageBox.Show("Сохранить изменения в базе?", "Выход",
                MessageBoxButtons.YesNoCancel, MessageBoxIcon.Question);
            if (answer == DialogResult.Cancel || (answer == DialogResult.Yes && !SaveAll()))
                e.Cancel = true;
        }
    }

    /// <summary>
    /// Подчинённая форма: заказы клиента, выбранного в главной форме.
    /// Привязана к той же BindingSource, поэтому при переходе по клиентам
    /// в главной форме список заказов здесь меняется автоматически.
    /// </summary>
    public class OrdersForm : Form
    {
        private readonly MainForm _main;
        private readonly BindingSource _ordersBs = new();
        private readonly DataGridView _grid = Grids.Create();
        private readonly Label _header = new()
        {
            Dock = DockStyle.Top,
            Height = 32,
            TextAlign = ContentAlignment.MiddleLeft,
            Font = new Font(SystemFonts.DefaultFont.FontFamily, 11, FontStyle.Bold)
        };
        private readonly Label _total = new()
        {
            Dock = DockStyle.Bottom,
            Height = 26,
            TextAlign = ContentAlignment.MiddleRight
        };

        public OrdersForm(MainForm main)
        {
            _main = main;
            Text = "Заказы — подчинённая форма";
            Width = 700;
            Height = 420;
            StartPosition = FormStartPosition.CenterParent;

            _ordersBs.DataSource = main.ClientsBinding;
            _ordersBs.DataMember = Db.RelationName;
            _grid.DataSource = _ordersBs;
            Grids.SetupOrders(_grid);

            var toolbar = new ToolStrip();
            toolbar.Items.Add("◀ Пред. клиент", null, (_, _) => main.ClientsBinding.MovePrevious());
            toolbar.Items.Add("След. клиент ▶", null, (_, _) => main.ClientsBinding.MoveNext());
            toolbar.Items.Add(new ToolStripSeparator());
            toolbar.Items.Add("Добавить заказ", null, (_, _) => _ordersBs.AddNew());
            toolbar.Items.Add("Удалить заказ", null, (_, _) => { if (_ordersBs.Current != null) _ordersBs.RemoveCurrent(); });
            toolbar.Items.Add(new ToolStripSeparator());
            toolbar.Items.Add("Сохранить", null, (_, _) => _main.SaveAll());

            Controls.Add(_grid);
            Controls.Add(_header);
            Controls.Add(_total);
            Controls.Add(toolbar);

            main.ClientsBinding.CurrentChanged += OnClientChanged;
            _ordersBs.ListChanged += (_, _) => UpdateTotal();
            FormClosed += (_, _) => main.ClientsBinding.CurrentChanged -= OnClientChanged;

            OnClientChanged(this, EventArgs.Empty);
        }

        public void EndEdit() => _ordersBs.EndEdit();

        private void OnClientChanged(object sender, EventArgs e)
        {
            _header.Text = _main.ClientsBinding.Current is DataRowView c
                ? $"Клиент: {c["FullName"]}   ({c["City"]}, {c["Phone"]})"
                : "Клиент не выбран";
            UpdateTotal();
        }

        private void UpdateTotal()
        {
            decimal sum = 0;
            foreach (DataRowView r in _ordersBs)
            {
                if (r["Quantity"] is int q && r["Price"] is decimal p)
                    sum += q * p;
            }
            _total.Text = $"Заказов: {_ordersBs.Count}    Итого: {sum:N2} ₽   ";
        }
    }

    /// <summary>Общая настройка DataGridView для обеих форм.</summary>
    internal static class Grids
    {
        public static DataGridView Create()
        {
            var g = new DataGridView
            {
                Dock = DockStyle.Fill,
                AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill,
                SelectionMode = DataGridViewSelectionMode.FullRowSelect,
                MultiSelect = false,
                AllowUserToAddRows = true,
                RowHeadersWidth = 30
            };
            g.DataError += (_, e) =>
            {
                MessageBox.Show("Некорректное значение: " + e.Exception?.Message, "Ошибка ввода",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                e.ThrowException = false;
            };
            return g;
        }

        public static void SetupClients(DataGridView g)
        {
            g.DataBindingComplete += (_, _) =>
            {
                Set(g, "ID", "Код", readOnly: true, weight: 15);
                Set(g, "FullName", "ФИО", weight: 45);
                Set(g, "Phone", "Телефон", weight: 25);
                Set(g, "City", "Город", weight: 25);
            };
        }

        public static void SetupOrders(DataGridView g)
        {
            g.DataBindingComplete += (_, _) =>
            {
                Set(g, "ID", "№", readOnly: true, weight: 10);
                Set(g, "ClientID", null);                 // внешний ключ скрываем
                Set(g, "OrderDate", "Дата", weight: 20, format: "dd.MM.yyyy");
                Set(g, "Product", "Товар", weight: 40);
                Set(g, "Quantity", "Кол-во", weight: 12);
                Set(g, "Price", "Цена", weight: 18, format: "N2");
            };
        }

        private static void Set(DataGridView g, string name, string header,
            bool readOnly = false, float weight = 20, string format = null)
        {
            var col = g.Columns[name];
            if (col == null) return;
            if (header == null) { col.Visible = false; return; }
            col.HeaderText = header;
            col.ReadOnly = readOnly;
            col.FillWeight = weight;
            if (format != null) col.DefaultCellStyle.Format = format;
        }
    }
}
