namespace AccessMasterDetail;

internal static class Program
{
    [STAThread]
    private static void Main()
    {
        ApplicationConfiguration.Initialize();
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
