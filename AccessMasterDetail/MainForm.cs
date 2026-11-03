using System;
using System.Data;
using System.Data.OleDb;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Windows.Forms;

namespace AccessMasterDetail
{
    /// <summary>Главная форма: список клиентов + встроенная подчинённая таблица заказов.</summary>
    public class MainForm : Form
    {
        private readonly DataSet _ds;
        private readonly BindingSource _clientsBs = new();
        private readonly BindingSource _ordersBs = new();
        private readonly DataGridView _clientsGrid = Grids.Create();
        private readonly DataGridView _ordersGrid = Grids.Create();
        private OrdersForm _ordersForm;

        // Фильтры
        private readonly TextBox _clientSearch = new() { Width = 180 };
        private readonly ComboBox _cityFilter = new() { Width = 130, DropDownStyle = ComboBoxStyle.DropDownList };
        private readonly TextBox _productSearch = new() { Width = 160 };
        private readonly TextBox _priceFrom = new() { Width = 80 };
        private readonly Label _clientsCount = new() { AutoSize = true, Margin = new Padding(12, 7, 0, 0) };
        private readonly Label _ordersCount = new() { AutoSize = true, Margin = new Padding(12, 7, 0, 0) };

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
            split.Panel1.Controls.Add(Filters.Panel(
                Filters.Label("ФИО / телефон:"), _clientSearch,
                Filters.Label("Город:"), _cityFilter,
                Filters.ClearButton(() => { _clientSearch.Clear(); _cityFilter.SelectedIndex = 0; }),
                _clientsCount));
            split.Panel1.Controls.Add(Caption("Клиенты (главная таблица)"));
            split.Panel2.Controls.Add(_ordersGrid);
            split.Panel2.Controls.Add(Filters.Panel(
                Filters.Label("Товар:"), _productSearch,
                Filters.Label("Цена от:"), _priceFrom,
                Filters.ClearButton(() => { _productSearch.Clear(); _priceFrom.Clear(); }),
                _ordersCount));
            split.Panel2.Controls.Add(Caption("Заказы выбранного клиента (подчинённая таблица)"));

            Controls.Add(split);
            Controls.Add(toolbar);

            _clientsGrid.CellDoubleClick += (_, _) => OpenOrdersForm();
            FormClosing += OnFormClosing;

            // Таблицы меняются сразу при вводе в фильтры
            FillCities();
            _cityFilter.DropDown += (_, _) => FillCities();
            _clientSearch.TextChanged += (_, _) => ApplyClientFilter();
            _cityFilter.SelectedIndexChanged += (_, _) => ApplyClientFilter();
            _productSearch.TextChanged += (_, _) => ApplyOrderFilter();
            _priceFrom.TextChanged += (_, _) => ApplyOrderFilter();
            _clientsBs.CurrentChanged += (_, _) => ApplyOrderFilter();
            _clientsBs.ListChanged += (_, _) => _clientsCount.Text = $"Найдено: {_clientsBs.Count}";
            _ordersBs.ListChanged += (_, _) => _ordersCount.Text = $"Найдено: {_ordersBs.Count}";
            ApplyClientFilter();
            ApplyOrderFilter();
        }

        private void FillCities()
        {
            var selected = _cityFilter.SelectedItem as string;
            _cityFilter.BeginUpdate();
            _cityFilter.Items.Clear();
            _cityFilter.Items.Add(Filters.All);
            var cities = new System.Collections.Generic.SortedSet<string>();
            foreach (DataRow r in _ds.Tables["Clients"].Rows)
                if (r.RowState != DataRowState.Deleted && r["City"] is string c && c.Trim() != "")
                    cities.Add(c.Trim());
            foreach (var c in cities) _cityFilter.Items.Add(c);
            _cityFilter.SelectedItem = selected != null && _cityFilter.Items.Contains(selected) ? selected : Filters.All;
            _cityFilter.EndUpdate();
        }

        private void ApplyClientFilter()
        {
            var parts = new System.Collections.Generic.List<string>();
            var text = _clientSearch.Text.Trim();
            if (text != "")
                parts.Add($"({Filters.Like("FullName", text)} OR {Filters.Like("Phone", text)})");
            if (_cityFilter.SelectedItem is string city && city != Filters.All)
                parts.Add($"City = '{Filters.Quote(city)}'");
            _clientsBs.Filter = string.Join(" AND ", parts);
            _clientsCount.Text = $"Найдено: {_clientsBs.Count}";
        }

        private void ApplyOrderFilter()
        {
            _ordersBs.Filter = Filters.OrdersFilter(_productSearch.Text, _priceFrom);
            _ordersCount.Text = $"Найдено: {_ordersBs.Count}";
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
}
