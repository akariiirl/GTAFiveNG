using CodeWalker.GameFiles;
using CodeWalker.Utils;
using System.Text.Json;
using System.Security.Cryptography;

if (args.Length == 2 && args[0] == "--validate-plan")
{
    var paths = ExtractionPlan.Load(args[1]);
    Console.WriteLine(JsonSerializer.Serialize(paths.Select(path => new { path, export = ExtractionPlan.ExportName(path) })));
    return 0;
}
if (args.Length == 2 && args[0] == "--inspect-ybn-xml")
{
    Console.WriteLine(JsonSerializer.Serialize(MetadataInventory.BoundsXY(XmlYbn.GetYbn(File.ReadAllText(args[1])).Bounds)));
    return 0;
}
if (args.Length == 3 && args[0] == "--bootstrap-fixture")
{
    using var fixture=JsonDocument.Parse(File.ReadAllText(args[1]));
    var sources=new List<CatalogSource>();
    foreach(var item in fixture.RootElement.EnumerateArray())
    {
        var path=ExtractionPlan.Normalize(item.GetProperty("path").GetString());
        var xml=item.TryGetProperty("xml",out var x)?x.GetString():null;
        var bounds=item.TryGetProperty("bounds_xml",out var b)?b.GetString():null;
        var fail=item.TryGetProperty("fail_decode",out var f)&&f.GetBoolean();
        sources.Add(new CatalogSource(path,(xml??bounds??"").Length,path[..(path.IndexOf(".rpf")+4)],MetadataInventory.Hash(path+(xml??"")+(bounds??"")),
            xml==null?null:()=>fail?throw new Exception("Synthetic decode failure"):xml,
            bounds==null?null:()=>MetadataInventory.BoundsXY(XmlYbn.GetYbn(bounds).Bounds)));
    }
    Directory.CreateDirectory(args[2]); var result=MetadataInventory.Run(args[2],sources);
    Console.WriteLine(JsonSerializer.Serialize(new{snapshot=result.Directory,errors=result.Errors})); return result.Errors==0?0:1;
}
// The source installation is opened only through CodeWalker's read APIs.
if (args.Length < 2) { Console.Error.WriteLine("Usage: AssetReader GTA_ROOT OUTPUT_DIRECTORY [name-filter]"); return 2; }
var root = Path.GetFullPath(args[0]);
var output = Path.GetFullPath(args[1]);
if (output.StartsWith(root + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase) || output == root)
    throw new ArgumentException("Output must be outside the game installation");
if (args.Length > 2 && args[2] == "--tasks" && args.Length != 4) throw new ArgumentException("--tasks requires a plan path");
var bootstrapMode = args.Length == 3 && args[2] == "--bootstrap";
var taskMode = args.Length == 4 && args[2] == "--tasks";
var taskPaths = taskMode ? ExtractionPlan.Load(args[3]).ToHashSet(StringComparer.OrdinalIgnoreCase) : null;
Directory.CreateDirectory(output);
using var taskLock = (taskMode || bootstrapMode) ? new FileStream(Path.Combine(output,".extraction.lock"),FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None) : null;
GTA5Keys.LoadFromPath(root);
var manager = new RpfManager();
using var errors = new StreamWriter(Path.Combine(output, "errors.log"), append:true);
errors.WriteLine("Run started " + DateTime.UtcNow.ToString("O"));
var cachePath = Path.Combine(output,"source-cache.json");
var cache = File.Exists(cachePath) ? JsonSerializer.Deserialize<Dictionary<string,string>>(File.ReadAllText(cachePath)) : new Dictionary<string,string>();
manager.Init(root, false, s => Console.WriteLine(s), s => { errors.WriteLine(s); errors.Flush(); }, rootOnly: !(taskMode || bootstrapMode));
var entries = manager.EntryDict.Values.OfType<RpfFileEntry>().OrderBy(e => e.Path).ToArray();
if (bootstrapMode)
{
    var hashes=new Dictionary<string,string>();
    var readerHash=MetadataInventory.Hash(Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(typeof(MetadataInventory).Assembly.Location))));
    var catalog=new List<CatalogSource>();
    foreach(var entry in entries)
    {
        var physicalPath=entry.Path.Replace('\\','/');
        var path=physicalPath.ToLowerInvariant();
        if (!new[]{".ymap",".ytyp",".ydr",".ydd",".yft",".ytd",".ybn"}.Contains(Path.GetExtension(path))) continue;
        var end=path.IndexOf(".rpf",StringComparison.OrdinalIgnoreCase); if(end<0) continue;
        var archive=path[..(end+4)];
        if(!hashes.TryGetValue(archive,out var hash))
        { using var stream=File.OpenRead(Path.Combine(root,physicalPath[..(end+4)].Replace('/',Path.DirectorySeparatorChar))); hash=Convert.ToHexString(SHA256.HashData(stream)); hashes[archive]=hash; }
        var fingerprint=MetadataInventory.Hash(readerHash+":"+hash+":"+path+":"+entry.GetFileSize());
        Func<string> metadata=path.EndsWith(".ymap") ? ()=>MetaXml.GetXml(manager.GetFile<YmapFile>(entry),out _) : path.EndsWith(".ytyp") ? ()=>MetaXml.GetXml(manager.GetFile<YtypFile>(entry),out _) : null;
        Func<float[]> bounds=path.EndsWith(".ybn") ? ()=>MetadataInventory.BoundsXY(manager.GetFile<YbnFile>(entry)?.Bounds) : null;
        catalog.Add(new CatalogSource(path,entry.GetFileSize(),archive,fingerprint,metadata,bounds));
    }
    var result=MetadataInventory.Run(output,catalog); Console.WriteLine(result.Directory); return result.Errors==0?0:1;
}
using var inventory = new StreamWriter(Path.Combine(output, "inventory.jsonl"));
foreach (var entry in entries)
    inventory.WriteLine(JsonSerializer.Serialize(new { path = entry.Path, name = entry.Name, size = entry.GetFileSize() }));
Console.WriteLine($"Indexed {entries.Length} resources across {manager.AllRpfs.Count} archives.");
if (args.Length > 2)
{
    HashSet<string> requested = null;
    if (!taskMode && args[2].StartsWith("@"))
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
    var failures = 0;
    var archiveFingerprints = new Dictionary<string,string>();
    var readerHash = taskMode ? Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(typeof(ExtractionPlan).Assembly.Location))) : "";
    if (taskMode)
    {
        var available = entries.Select(e => e.Path.Replace('\\', '/')).ToHashSet(StringComparer.OrdinalIgnoreCase);
        foreach (var missing in taskPaths.Where(path => !available.Contains(path)))
        { errors.WriteLine("Missing exact task: " + missing); failures++; }
    }
    foreach (var e in entries.Where(e => taskMode ? taskPaths.Contains(e.Path.Replace('\\', '/')) : requested != null ? requested.Contains(Path.GetFileNameWithoutExtension(e.Name)) : e.Name.Contains(args[2], StringComparison.OrdinalIgnoreCase)))
    {
        try
        {
            var dest = Path.Combine(output, taskMode ? ExtractionPlan.ExportName(e.Path)[..^4] : e.Path.Replace('\\', '/').Replace('/', '_'));
            var exportFolder = taskMode ? Path.Combine(output, "textures", Path.GetFileName(dest)) : output;
            Directory.CreateDirectory(exportFolder);
            var normalizedPath = e.Path.Replace('\\', '/');
            var archiveEnd = normalizedPath.IndexOf(".rpf", StringComparison.OrdinalIgnoreCase);
            if (archiveEnd < 0) throw new InvalidDataException("Resource has no archive path");
            var archive = new FileInfo(Path.Combine(root,normalizedPath[..(archiveEnd+4)].Replace('/',Path.DirectorySeparatorChar)));
            var fingerprint = $"reader-v2:{archive.Length}:{archive.LastWriteTimeUtc.Ticks}:{e.GetFileSize()}";
            var receiptPath = dest + ".receipt.json";
            if (taskMode)
            {
                if (!archiveFingerprints.TryGetValue(archive.FullName,out var archiveHash))
                {
                    using var archiveStream = archive.OpenRead();
                    archiveHash = Convert.ToHexString(SHA256.HashData(archiveStream));
                    archiveFingerprints[archive.FullName] = archiveHash;
                }
                fingerprint = "reader-tasks-v1:" + readerHash + ":" + archiveHash + ":" + e.GetFileSize();
                if (File.Exists(receiptPath))
                {
                    var receipt = JsonSerializer.Deserialize<TaskReceipt>(File.ReadAllText(receiptPath));
                    if (receipt.Fingerprint == fingerprint && receipt.Files.ContainsKey(Path.GetRelativePath(output,dest+".xml").Replace('\\','/')) && receipt.Files.All(pair => File.Exists(Path.Combine(output,pair.Key)) && Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(Path.Combine(output,pair.Key)))) == pair.Value))
                        continue;
                    throw new IOException("Existing task output changed or invalid; preserve it and choose a fresh output directory");
                }
                if (File.Exists(dest + ".xml") || Directory.EnumerateFiles(exportFolder, "*", SearchOption.AllDirectories).Any())
                    throw new IOException("Incomplete task output preserved; choose a fresh output directory");
            }
            else if (File.Exists(dest + ".xml") && cache.TryGetValue(e.Path,out var previous) && previous==fingerprint) continue;
            string xml = null;
            if (e.Name.EndsWith(".ybn")) xml = YbnXml.GetXml(manager.GetFile<YbnFile>(e));
            if (e.Name.EndsWith(".ydr")) xml = YdrXml.GetXml(manager.GetFile<YdrFile>(e), exportFolder);
            if (e.Name.EndsWith(".ymap")) xml = MetaXml.GetXml(manager.GetFile<YmapFile>(e), out _);
            if (e.Name.EndsWith(".ytyp")) xml = MetaXml.GetXml(manager.GetFile<YtypFile>(e), out _);
            if (e.Name.EndsWith(".ytd")) xml = YtdXml.GetXml(manager.GetFile<YtdFile>(e), exportFolder);
            if (e.Name.EndsWith(".yft")) xml = YftXml.GetXml(manager.GetFile<YftFile>(e), exportFolder);
            if (e.Name.EndsWith(".ydd")) xml = YddXml.GetXml(manager.GetFile<YddFile>(e), exportFolder);
            if (taskMode && xml == null) throw new InvalidDataException("Task produced no XML");
            if (xml != null)
            {
                File.WriteAllText(dest+".xml.tmp",xml);
                File.Move(dest+".xml.tmp",dest+".xml",!taskMode);
                if (taskMode)
                {
                    var files = Directory.EnumerateFiles(exportFolder,"*",SearchOption.AllDirectories).Append(dest+".xml")
                        .ToDictionary(path => Path.GetRelativePath(output,path).Replace('\\','/'), path => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))));
                    File.WriteAllText(receiptPath+".tmp",JsonSerializer.Serialize(new TaskReceipt(fingerprint,files)));
                    File.Move(receiptPath+".tmp",receiptPath,false);
                }
                cache[e.Path]=fingerprint;
                File.WriteAllText(cachePath+".tmp",JsonSerializer.Serialize(cache));
                File.Move(cachePath+".tmp",cachePath,true);
                Console.WriteLine("Exported " + e.Name);
            }
        }
        catch (Exception ex) { errors.WriteLine(e.Path + ": " + ex); errors.Flush(); failures++; }
    }
    if (taskMode && failures > 0) return 1;
}
return 0;

public record TaskReceipt(string Fingerprint, Dictionary<string,string> Files);
