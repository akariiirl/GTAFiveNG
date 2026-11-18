"""Verified local immutable drawable cache. Never use pickle or overwrite entries."""
import hashlib
import json
from pathlib import Path
import re
import os
import tempfile


class ResourceCache:
    def __init__(self, root, recover=False):
        self.root = Path(root)
        self.hits = self.misses = self.recovered = 0
        self.recover = recover
        self.pipeline = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}

    def path(self, key):
        if not re.fullmatch('[0-9a-f]{64}', key): raise ValueError('Invalid cache key')
        return self.root/key[:2]/(key+'.json')

    def get(self, key):
        path = self.path(key)
        if not path.exists(): self.misses += 1; return None
        try:
            envelope = json.loads(path.read_text(encoding='utf-8'))
            if envelope.get('key') != key: raise ValueError('Shared cache key mismatch')
            payload = envelope['payload']
            if envelope['sha256'] != hashlib.sha256(payload.encode()).hexdigest():
                raise ValueError('Corrupt shared cache entry: '+key)
            result=json.loads(payload)
        except (ValueError,KeyError,TypeError):
            if not self.recover: raise
            self.quarantine(path); self.misses += 1; return None
        self.hits += 1
        return result

    def quarantine(self, path):
        import uuid
        folder=self.root/'quarantine'; folder.mkdir(parents=True,exist_ok=True)
        path.rename(folder/(path.name+'.'+uuid.uuid4().hex))
        self.recovered += 1

    def put(self, key, value):
        path = self.path(key)
        payload = json.dumps(value, allow_nan=False, separators=(',',':'))
        envelope = json.dumps({'key':key,'sha256':hashlib.sha256(payload.encode()).hexdigest(),'payload':payload},separators=(',',':'))
        path.parent.mkdir(parents=True,exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(dir=path.parent,suffix='.tmp')
        try:
            with os.fdopen(descriptor,'w',encoding='utf-8') as stream:
                stream.write(envelope); stream.flush(); os.fsync(stream.fileno())
            try:
                # Atomic no-clobber publication; an interrupted write never appears as an entry.
                os.link(temporary,path)
            except FileExistsError:
                if self.get(key) != value: raise ValueError('Conflicting immutable cache entry')
        finally:
            Path(temporary).unlink(missing_ok=True)


def cached_drawable(cache, xml, name, materials, textures, report, convert):
    """Cache geometry and replay material/texture/report effects on each build."""
    import numpy as np
    path, member = xml if isinstance(xml,tuple) else (xml,None)
    config = {'schema':1,'numpy':np.__version__,'source':hashlib.sha256(path.read_bytes()).hexdigest(),'member':member,'name':name,
              'textures':{k:v.get('target',k+'.dds') for k,v in sorted(textures.items())},'pipeline':cache.pipeline}
    key = hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
    entry = cache.get(key)
    if entry is None:
        local_materials = {}; local_textures = {k:{**v,'used':False} for k,v in textures.items()}
        local_report = {'missing_textures':set(),'degenerate_triangles_removed':0,'nonfinite_attribute_triangles_removed':0}
        meshes = convert(xml,name,local_materials,local_textures,local_report)
        entry = {'meshes':[{k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in mesh.items()} for mesh in meshes],
                 'materials':local_materials,'used_textures':[k for k,v in local_textures.items() if v['used']],
                 'missing_textures':sorted(local_report['missing_textures']),
                 'skipped_skinned_models':sorted(local_report.get('skipped_skinned_models',set())),
                 'degenerate_triangles_removed':local_report['degenerate_triangles_removed'],
                 'nonfinite_attribute_triangles_removed':local_report['nonfinite_attribute_triangles_removed'],
                 'terrain_layered_triangles':local_report.get('terrain_layered_triangles',0),
                 'terrain_textured_triangles':local_report.get('terrain_textured_triangles',0),
                 'terrain_unresolved':sorted(local_report.get('terrain_unresolved',set()))}
        cache.put(key,entry)
    materials.update(entry['materials'])
    for key in entry['used_textures']: textures[key]['used'] = True
    report['missing_textures'].update(entry['missing_textures'])
    report['degenerate_triangles_removed'] += entry['degenerate_triangles_removed']
    report['nonfinite_attribute_triangles_removed'] = report.get('nonfinite_attribute_triangles_removed',0) + entry.get('nonfinite_attribute_triangles_removed',0)
    for metric in ('terrain_layered_triangles','terrain_textured_triangles'):
        if entry.get(metric): report[metric] = report.get(metric,0) + entry[metric]
    if entry.get('terrain_unresolved'): report.setdefault('terrain_unresolved',set()).update(entry['terrain_unresolved'])
    if entry['skipped_skinned_models']: report.setdefault('skipped_skinned_models',set()).update(entry['skipped_skinned_models'])
    return [{k:np.asarray(v,dtype=int if k=='i' else float) if k in ('v','i','n','uv') and v is not None else v for k,v in mesh.items()} for mesh in entry['meshes']]


def hash_file(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''): digest.update(block)
    return digest.hexdigest()


def cached_collision(cache, xml, origin, report, convert):
    """Store world-space collision once; translate independently for each region."""
    import collections
    import numpy as np
    config={'operation':'collision-v1','source':hash_file(xml),'numpy':np.__version__,'pipeline':cache.pipeline}
    key=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
    entry=cache.get(key)
    if entry is None:
        local={'unsupported_collision':collections.Counter(),'degenerate_triangles_removed':0}
        meshes=convert(xml,np.zeros(3),local)
        entry={'meshes':[{k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in mesh.items()} for mesh in meshes],
               'unsupported':dict(local['unsupported_collision']),'degenerate':local['degenerate_triangles_removed']}
        cache.put(key,entry)
    report['unsupported_collision'].update(entry['unsupported'])
    report['degenerate_triangles_removed']+=entry['degenerate']
    meshes=[{**m,'v':np.asarray(m['v'],dtype=float)-origin,'i':np.asarray(m['i'],dtype=int)} for m in entry['meshes']]
    return meshes


def cached_texture(cache, source, target, normalize):
    """Verified binary payloads stream to new output files on cache hits."""
    import shutil
    config={'operation':'normalized-dds-v1','source':hash_file(source),'pipeline':cache.pipeline}
    key=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
    entry=cache.get(key)
    if entry is not None:
        blob=cache.root/'blobs'/(entry['sha256']+'.bin')
        if not blob.is_file() or hash_file(blob)!=entry['sha256']:
            if not cache.recover: raise ValueError('Corrupt texture cache payload')
            cache.quarantine(cache.path(key))
            if blob.exists(): cache.quarantine(blob)
            entry=None
    if entry is None:
        data,repaired=normalize(Path(source).read_bytes())
        digest=hashlib.sha256(data).hexdigest(); blob=cache.root/'blobs'/(digest+'.bin')
        blob.parent.mkdir(parents=True,exist_ok=True)
        if blob.exists() and hash_file(blob)!=digest:
            if not cache.recover: raise ValueError('Corrupt texture cache payload')
            cache.quarantine(blob)
        descriptor,temporary=tempfile.mkstemp(dir=blob.parent,suffix='.tmp')
        try:
            with os.fdopen(descriptor,'wb') as stream:
                stream.write(data); stream.flush(); os.fsync(stream.fileno())
            try: os.link(temporary,blob)
            except FileExistsError:
                if hash_file(blob)!=digest: raise ValueError('Conflicting texture cache payload')
        finally: Path(temporary).unlink(missing_ok=True)
        entry={'sha256':digest,'repaired':bool(repaired)}; cache.put(key,entry)
    shutil.copyfile(blob,target)
    return entry['repaired']
