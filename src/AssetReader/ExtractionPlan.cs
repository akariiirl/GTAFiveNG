using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

// Source-only task protocol: no installation, keys or archive APIs required.
public static class ExtractionPlan
{
    public static string Normalize(string path)
    {
        path = path.Replace('\\', '/').ToLowerInvariant();
        if (string.IsNullOrWhiteSpace(path) || path.StartsWith('/') || path.Contains(':') || path.Split('/').Any(x => x is "" or "." or ".."))
            throw new ArgumentException("Unsafe resource path");
        var extension = Path.GetExtension(path);
        if (!new[] { ".ymap", ".ytyp", ".ydr", ".ydd", ".yft", ".ytd", ".ybn" }.Contains(extension))
            throw new ArgumentException("Unsupported resource extension");
        return path;
    }
    public static string[] Load(string path)
    {
        using var document = JsonDocument.Parse(File.ReadAllText(path));
        if (document.RootElement.GetProperty("schema").GetInt32() != 1) throw new ArgumentException("Unsupported plan schema");
        return document.RootElement.GetProperty("tasks").EnumerateArray()
            .Select(task => Normalize(task.GetProperty("path").GetString())).Distinct().OrderBy(x => x, StringComparer.Ordinal).ToArray();
    }
    public static string ExportName(string path)
    {
        path = Normalize(path);
        var hash = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(path))).ToLowerInvariant();
        return "resource_" + hash + ".rpf_" + path.Split('/').Last() + ".xml";
    }
}
