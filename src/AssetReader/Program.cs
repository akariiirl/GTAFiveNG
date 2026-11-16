using CodeWalker.GameFiles;
using CodeWalker.Utils;
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
using var errors = new StreamWriter(Path.Combine(output, "errors.log"), append:true);
errors.WriteLine("Run started " + DateTime.UtcNow.ToString("O"));
var cachePath = Path.Combine(output,"source-cache.json");
var cache = File.Exists(cachePath) ? JsonSerializer.Deserialize<Dictionary<string,string>>(File.ReadAllText(cachePath)) : new Dictionary<string,string>();
manager.Init(root, false, s => Console.WriteLine(s), s => { errors.WriteLine(s); errors.Flush(); }, rootOnly: true);
using var inventory = new StreamWriter(Path.Combine(output, "inventory.jsonl"));
var entries = manager.EntryDict.Values.OfType<RpfFileEntry>().OrderBy(e => e.Path).ToArray();
foreach (var entry in entries)
    inventory.WriteLine(JsonSerializer.Serialize(new { path = entry.Path, name = entry.Name, size = entry.GetFileSize() }));
Console.WriteLine($"Indexed {entries.Length} resources across {manager.AllRpfs.Count} archives.");
if (args.Length > 2)
{
    HashSet<string> requested = null;
    if (args[2].StartsWith("@"))
    {
        var report = JsonDocument.Parse(File.ReadAllText(args[2][1..]));
        requested = report.RootElement.GetProperty("missing_assets").EnumerateArray().Select(x => x.GetString()).ToHashSet(StringComparer.OrdinalIgnoreCase);
        var missingTextures = report.RootElement.GetProperty("missing_textures").EnumerateArray().Select(x => x.GetString()).ToHashSet(StringComparer.OrdinalIgnoreCase);
        var textureSources = new Dictionary<string,string>();
        foreach (var e in entries.Where(e => e.Name.EndsWith(".ytd") && (e.Path.Contains("gtxd.rpf") || e.Path.Contains("\\props\\"))))
        {
            if (missingTextures.Count == 0) break;
            try
            {
                var td = manager.GetFile<YtdFile>(e)?.TextureDict?.Textures?.data_items;
                if (td == null) continue;
                foreach (var tex in td.Where(t => missingTextures.Contains(t.Name)))
                {
                    var dest = Path.Combine(output, Path.GetFileName(tex.Name).ToLowerInvariant()+".dds");
                    File.WriteAllBytes(dest, DDSIO.GetDDSFile(tex));
                    textureSources[tex.Name] = e.Path;
                    missingTextures.Remove(tex.Name);
                    Console.WriteLine("Resolved texture " + tex.Name);
                }
            }
            catch (Exception ex) { errors.WriteLine(e.Path + ": " + ex.Message); }
        }
        File.WriteAllText(Path.Combine(output,"resolved-textures.json"), JsonSerializer.Serialize(textureSources));
    }
    foreach (var e in entries.Where(e => requested != null ? requested.Contains(Path.GetFileNameWithoutExtension(e.Name)) : e.Name.Contains(args[2], StringComparison.OrdinalIgnoreCase)))
    {
        try
        {
            var dest = Path.Combine(output, e.Path.Replace('\\', '/').Replace('/', '_'));
            var archive = new FileInfo(Path.Combine(root,e.Path.Split('\\','/')[0]));
            var fingerprint = $"reader-v2:{archive.Length}:{archive.LastWriteTimeUtc.Ticks}:{e.GetFileSize()}";
            if (File.Exists(dest + ".xml") && cache.TryGetValue(e.Path,out var previous) && previous==fingerprint) continue;
            string xml = null;
            if (e.Name.EndsWith(".ybn")) xml = YbnXml.GetXml(manager.GetFile<YbnFile>(e));
            if (e.Name.EndsWith(".ydr")) xml = YdrXml.GetXml(manager.GetFile<YdrFile>(e), output);
            if (e.Name.EndsWith(".ymap")) xml = MetaXml.GetXml(manager.GetFile<YmapFile>(e), out _);
            if (e.Name.EndsWith(".ytyp")) xml = MetaXml.GetXml(manager.GetFile<YtypFile>(e), out _);
            if (e.Name.EndsWith(".ytd")) xml = YtdXml.GetXml(manager.GetFile<YtdFile>(e), output);
            if (e.Name.EndsWith(".yft")) xml = YftXml.GetXml(manager.GetFile<YftFile>(e), output);
            if (e.Name.EndsWith(".ydd")) xml = YddXml.GetXml(manager.GetFile<YddFile>(e), output);
            if (xml != null)
            {
                File.WriteAllText(dest+".xml.tmp",xml);
                File.Move(dest+".xml.tmp",dest+".xml",true);
                cache[e.Path]=fingerprint;
                File.WriteAllText(cachePath+".tmp",JsonSerializer.Serialize(cache));
                File.Move(cachePath+".tmp",cachePath,true);
                Console.WriteLine("Exported " + e.Name);
            }
        }
        catch (Exception ex) { errors.WriteLine(e.Path + ": " + ex); errors.Flush(); }
    }
}
return 0;
