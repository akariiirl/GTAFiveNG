using CodeWalker.GameFiles;
using System.Text.Json;

// The source installation is opened only through CodeWalker's read APIs.
if (args.Length < 2) { Console.Error.WriteLine("Usage: AssetReader GTA_ROOT OUTPUT_DIRECTORY [name-filter]"); return 2; }
var root = Path.GetFullPath(args[0]);
var output = Path.GetFullPath(args[1]);
if (output.StartsWith(root + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase) || output == root)
    throw new ArgumentException("Output must be outside the game installation");
Directory.CreateDirectory(output);
GTA5Keys.LoadFromPath(root);
var manager = new RpfManager();
using var errors = new StreamWriter(Path.Combine(output, "errors.log"));
manager.Init(root, false, s => Console.WriteLine(s), s => { errors.WriteLine(s); errors.Flush(); }, rootOnly: true);
using var inventory = new StreamWriter(Path.Combine(output, "inventory.jsonl"));
var entries = manager.EntryDict.Values.OfType<RpfFileEntry>().OrderBy(e => e.Path).ToArray();
foreach (var entry in entries)
    inventory.WriteLine(JsonSerializer.Serialize(new { path = entry.Path, name = entry.Name, size = entry.GetFileSize() }));
Console.WriteLine($"Indexed {entries.Length} resources across {manager.AllRpfs.Count} archives.");
if (args.Length > 2)
{
    foreach (var e in entries.Where(e => e.Name.Contains(args[2], StringComparison.OrdinalIgnoreCase)))
    {
        try
        {
            var dest = Path.Combine(output, e.Path.Replace('\\', '/').Replace('/', '_'));
            if (File.Exists(dest + ".xml")) continue;
            string xml = null;
            if (e.Name.EndsWith(".ybn")) xml = YbnXml.GetXml(manager.GetFile<YbnFile>(e));
            if (e.Name.EndsWith(".ydr")) xml = YdrXml.GetXml(manager.GetFile<YdrFile>(e), output);
            if (xml != null) { File.WriteAllText(dest + ".xml", xml); Console.WriteLine("Exported " + e.Name); }
        }
        catch (Exception ex) { errors.WriteLine(e.Path + ": " + ex); errors.Flush(); }
    }
}
return 0;
