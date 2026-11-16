using CodeWalker.GameFiles;
using System.Reflection;
using System.Text.Json;

if (args.Length != 2) throw new ArgumentException("GTA root and new output path required");
var gameRoot=Path.GetFullPath(args[0]).TrimEnd(Path.DirectorySeparatorChar,Path.AltDirectorySeparatorChar);
var output=Path.GetFullPath(args[1]);
if (!Directory.Exists(gameRoot)) throw new DirectoryNotFoundException(gameRoot);
if (output.Equals(gameRoot,StringComparison.OrdinalIgnoreCase) || output.StartsWith(gameRoot+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))
    throw new ArgumentException("Output must be outside the game installation");
if (File.Exists(output)) throw new IOException("Preserving existing output");
var failures = new List<string>();
GTA5Keys.LoadFromPath(args[0]);
var manager = new RpfManager();
manager.Init(args[0], false, _ => {}, s => failures.Add(s), rootOnly:false);
var cache = new GameFileCache(1024*1024, 60, args[0], false, "", false, "");
cache.RpfMan=manager;
var t=typeof(GameFileCache);
void Set(string field, object value) => t.GetField(field, BindingFlags.NonPublic | BindingFlags.Instance).SetValue(cache,value);
void Property(string name, object value) => t.GetProperty(name).SetValue(cache,value);
void Run(string method) => t.GetMethod(method, BindingFlags.NonPublic | BindingFlags.Instance).Invoke(cache,null);
Set("ErrorLog", (Action<string>)(s => failures.Add(s)));
Set("UpdateStatus", (Action<string>)(_ => {}));
Property("BaseRpfs",manager.BaseRpfs); Property("AllRpfs",manager.AllRpfs); Property("DlcRpfs",manager.DlcRpfs);
cache.EnableDlc=true;
Run("InitDlcList"); Run("InitActiveMapRpfFiles");
Run("InitGlobalDicts"); Run("InitMapDicts"); Run("InitArchetypeDicts");
Run("InitManifestDicts"); Run("InitGtxds");
var parents=(Dictionary<MetaHash,MetaHash>)t.GetField("textureParents",BindingFlags.NonPublic|BindingFlags.Instance).GetValue(cache);
var archetypes=(Dictionary<uint,Archetype>)t.GetField("archetypeDict",BindingFlags.NonPublic|BindingFlags.Instance).GetValue(cache);
Dictionary<string,string> Paths(Dictionary<uint,RpfFileEntry> dict) => dict.ToDictionary(x=>x.Key.ToString(),x=>x.Value.Path);
var result=new {
    schema=1,
    expectedCodeWalkerCommit="485d56bec00262ed7fa472261cce7bbc6202b96e",
    assemblySha256=Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(File.ReadAllBytes(t.Assembly.Location))),
    methods=new[]{"InitDlcList","InitActiveMapRpfFiles","InitGlobalDicts","InitMapDicts","InitArchetypeDicts","InitManifestDicts","InitGtxds"},
    caveat="CodeWalker active map approximation; not verified against GTA runtime; see pinned implementation limitations",
    selectedDlc=cache.SelectedDlc,
    setup=cache.DlcSetupFiles.Select(x=>new {x.order, path=x.DlcFile?.Path}).ToArray(),
    active=cache.ActiveMapRpfFiles.ToDictionary(x=>x.Key,x=>x.Value.Path),
    patches=cache.DlcPatchedPaths,
    textureParents=parents.ToDictionary(x=>((uint)x.Key).ToString(),x=>((uint)x.Value).ToString()),
    ymap=Paths(cache.YmapDict), ybn=Paths(cache.YbnDict), ydr=Paths(cache.YdrDict), ydd=Paths(cache.YddDict), ytd=Paths(cache.YtdDict), yft=Paths(cache.YftDict),
    archetypes=archetypes.ToDictionary(x=>x.Key.ToString(),x=>x.Value.Ytyp.RpfFileEntry.Path),
    ytyp=cache.YtypDict.ToDictionary(x=>x.Key.ToString(),x=>x.Value.RpfFileEntry.Path),
    failures
};
using (var stream=new FileStream(output,FileMode.CreateNew,FileAccess.Write)) JsonSerializer.Serialize(stream,result);
Console.WriteLine($"Active map archives: {result.active.Count}; patch mappings: {result.patches.Count}; errors: {failures.Count}");
