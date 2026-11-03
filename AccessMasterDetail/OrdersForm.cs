using System;
using System.Data;
using System.Data.OleDb;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Windows.Forms;

namespace AccessMasterDetail
{
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
}
