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
}
