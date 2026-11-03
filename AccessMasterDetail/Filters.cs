using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.Windows.Forms;

namespace AccessMasterDetail
{
    /// <summary>Фильтры для таблиц: строка фильтра для BindingSource.Filter и панель с полями ввода.</summary>
    internal static class Filters
    {
        public const string All = "(все)";

        /// <summary>Экранирует кавычки для выражения фильтра DataView.</summary>
        public static string Quote(string s) => s.Replace("'", "''");

        /// <summary>Условие «столбец содержит текст» (без учёта регистра).</summary>
        public static string Like(string column, string text)
        {
            var sb = new System.Text.StringBuilder();
            foreach (var ch in text)
            {
                if (ch == '*' || ch == '%' || ch == '[' || ch == ']') sb.Append('[').Append(ch).Append(']');
                else if (ch == '\'') sb.Append("''");
                else sb.Append(ch);
            }
            return $"{column} LIKE '%{sb}%'";
        }

        /// <summary>Фильтр заказов: по названию товара и минимальной цене.</summary>
        public static string OrdersFilter(string product, TextBox priceFrom)
        {
            var parts = new List<string>();
            product = product.Trim();
            if (product != "") parts.Add(Like("Product", product));

            var priceText = priceFrom.Text.Trim().Replace(" ", "").Replace(',', '.');
            if (priceText == "")
                priceFrom.BackColor = SystemColors.Window;
            else if (decimal.TryParse(priceText, NumberStyles.Number, CultureInfo.InvariantCulture, out var price))
            {
                priceFrom.BackColor = SystemColors.Window;
                parts.Add("Price >= " + price.ToString(CultureInfo.InvariantCulture));
            }
            else
                priceFrom.BackColor = Color.MistyRose; // введено не число

            return string.Join(" AND ", parts);
        }

        public static FlowLayoutPanel Panel(params Control[] controls)
        {
            var p = new FlowLayoutPanel
            {
                Dock = DockStyle.Top,
                Height = 32,
                WrapContents = false,
                Padding = new Padding(2, 3, 2, 0)
            };
            p.Controls.AddRange(controls);
            return p;
        }

        public static Label Label(string text) => new Label
        {
            Text = text,
            AutoSize = true,
            Margin = new Padding(6, 7, 2, 0)
        };

        public static Button ClearButton(Action clear)
        {
            var b = new Button { Text = "Сбросить", AutoSize = true, Margin = new Padding(8, 0, 0, 0) };
            b.Click += (_, _) => clear();
            return b;
        }
    }
}
