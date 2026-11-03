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

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            try
            {
                Db.EnsureDatabase();
            }
            catch
            {
                // Драйвер Access недоступен — работаем в резервном режиме (данные в Shop.xml)
                Db.Offline = true;
            }
            var form = new MainForm();
            if (Db.Offline) form.Text += " — резервный режим (Shop.xml)";
            Application.Run(form);
        }
    }
}
