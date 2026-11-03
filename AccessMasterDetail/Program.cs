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
            catch (Exception ex)
            {
                MessageBox.Show(
                    "Не удалось открыть/создать базу Access.\n\n" + ex.Message,
                    "Ошибка", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }
            Application.Run(new MainForm());
        }
    }
}
