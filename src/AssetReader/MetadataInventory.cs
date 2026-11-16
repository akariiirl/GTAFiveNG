using CodeWalker.GameFiles;
using SharpDX;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

public record CatalogSource(string Path, long Size, string Archive, string Fingerprint, Func<string> Metadata = null, Func<float[]> Bounds = null);
public static class MetadataInventory
{
    public static string Hash(string text) => Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(text))).ToLowerInvariant();
    public static float[] BoundsXY(Bounds bounds)
    {
        if (bounds == null) return null;
        var points = new List<Vector3>();
        void Visit(Bounds b, Matrix parent)
        {
            if (b == null) throw new InvalidDataException("Missing composite child");
            var matrix = b.Transform * parent;
            var lo = b.BoxMin; var hi = b.BoxMax;
            if (!new[] { lo.X,lo.Y,lo.Z,hi.X,hi.Y,hi.Z }.All(float.IsFinite) || lo.X>hi.X || lo.Y>hi.Y || lo.Z>hi.Z)
                throw new InvalidDataException("Invalid native collision bounds");
            foreach (var x in new[] {lo.X,hi.X}) foreach (var y in new[] {lo.Y,hi.Y}) foreach (var z in new[] {lo.Z,hi.Z})
            {
                var p = Vector3.TransformCoordinate(new Vector3(x,y,z),matrix);
                if (!new[]{p.X,p.Y,p.Z}.All(float.IsFinite)) throw new InvalidDataException("Invalid collision transform");
                points.Add(p);
            }
            if (b is BoundComposite composite && composite.Children?.data_items != null)
                foreach (var child in composite.Children.data_items) Visit(child,matrix);
        }
        Visit(bounds,Matrix.Identity);
        return new[]{points.Min(p=>p.X),points.Min(p=>p.Y),points.Max(p=>p.X),points.Max(p=>p.Y)};
    }
    static void Publish(string path,string text)
    {
        if (File.Exists(path))
        { if (File.ReadAllText(path)!=text) throw new IOException("Preserving changed inventory output: "+path); return; }
        var temporary=path+".tmp"; File.WriteAllText(temporary,text); File.Move(temporary,path,false);
    }
    public static (string Directory,int Errors) Run(string output,IEnumerable<CatalogSource> sources)
    {
        var entries=sources.OrderBy(e=>e.Path,StringComparer.Ordinal).ToArray();
        var id=Hash(string.Join("\n",entries.Select(e=>e.Path+":"+e.Fingerprint)));
        var directory=System.IO.Path.Combine(output,"snapshots",id); System.IO.Directory.CreateDirectory(directory);
        var records=new List<string>(); var errors=0;
        foreach (var entry in entries)
        {
            var receipt=System.IO.Path.Combine(directory,Hash(entry.Path)+".index.json");
            try
            {
                string record;
                if (File.Exists(receipt))
                {
                    using var cached=JsonDocument.Parse(File.ReadAllText(receipt));
                    record=cached.RootElement.GetProperty("record").GetString();
                    if (Hash(record)!=cached.RootElement.GetProperty("sha256").GetString()) throw new IOException("Corrupt inventory checkpoint");
                    using var data=JsonDocument.Parse(record);
                    if(data.RootElement.GetProperty("source_fingerprint").GetString()!=entry.Fingerprint || data.RootElement.GetProperty("path").GetString()!=entry.Path) throw new IOException("Inventory checkpoint fingerprint mismatch");
                    if (data.RootElement.TryGetProperty("xml",out var xml) && xml.ValueKind!=JsonValueKind.Null)
                    {
                        var file=System.IO.Path.Combine(directory,xml.GetString());
                        if (!File.Exists(file) || Hash(File.ReadAllText(file))!=data.RootElement.GetProperty("xml_sha256").GetString()) throw new IOException("Corrupt bootstrap XML");
                    }
                }
                else
                {
                    var xml=entry.Metadata?.Invoke(); var bounds=entry.Bounds?.Invoke(); string filename=null;
                    if (xml!=null) { filename=ExtractionPlan.ExportName(entry.Path); Publish(System.IO.Path.Combine(directory,filename),xml); }
                    record=JsonSerializer.Serialize(new {path=entry.Path,name=entry.Path.Split('/').Last(),size=entry.Size,
                        archive=entry.Archive,source_fingerprint=entry.Fingerprint,bounds_xy=bounds,xml=filename,
                        xml_sha256=xml==null?null:Hash(xml),hash_only_references=xml==null?Array.Empty<string>():Regex.Matches(xml,@"hash_[0-9a-fA-F]{8}").Select(m=>m.Value).Distinct().OrderBy(x=>x).ToArray(),
                        precedence_evidence="Archive provenance only; active mount priority not inferred"});
                    Publish(receipt,JsonSerializer.Serialize(new {record,sha256=Hash(record)}));
                }
                records.Add(record);
            }
            catch(Exception ex) { errors++; records.Add(JsonSerializer.Serialize(new{path=entry.Path,error=ex.Message})); }
        }
        if(errors==0) Publish(System.IO.Path.Combine(directory,"inventory.jsonl"),string.Join("\n",records)+"\n");
        File.WriteAllText(System.IO.Path.Combine(output,"bootstrap.json.tmp"),JsonSerializer.Serialize(new {schema=1,snapshot=directory,errors,in_game_verified=false}));
        File.Move(System.IO.Path.Combine(output,"bootstrap.json.tmp"),System.IO.Path.Combine(output,"bootstrap.json"),true);
        if(errors>0) File.WriteAllText(System.IO.Path.Combine(directory,"index-errors.jsonl"),string.Join("\n",records));
        return (directory,errors);
    }
}
