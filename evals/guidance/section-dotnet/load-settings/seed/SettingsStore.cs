namespace Example.Settings;

public sealed class AppSettings
{
    public string Region { get; set; } = "us-east";
    public int Port { get; set; } = 8080;
}

public sealed class SettingsStore
{
    private readonly string _path;

    public SettingsStore(string path)
    {
        _path = path;
    }
}
