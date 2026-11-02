namespace AccessMasterDetail;

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
