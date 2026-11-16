"""Verified local immutable drawable cache. Never use pickle or overwrite entries."""
import hashlib
import json
from pathlib import Path
import re
import os
import tempfile


class ResourceCache:
    def __init__(self, root):
        self.root = Path(root)
        self.hits = self.misses = 0
        self.pipeline = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}

    def path(self, key):
        if not re.fullmatch('[0-9a-f]{64}', key): raise ValueError('Invalid cache key')
        return self.root/key[:2]/(key+'.json')

    def get(self, key):
        path = self.path(key)
        if not path.exists(): self.misses += 1; return None
        envelope = json.loads(path.read_text(encoding='utf-8'))
        if envelope.get('key') != key: raise ValueError('Shared cache key mismatch')
        payload = envelope['payload']
        if envelope['sha256'] != hashlib.sha256(payload.encode()).hexdigest():
            raise ValueError('Corrupt shared cache entry: '+key)
        self.hits += 1
        return json.loads(payload)

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
        local_report = {'missing_textures':set(),'degenerate_triangles_removed':0}
        meshes = convert(xml,name,local_materials,local_textures,local_report)
        entry = {'meshes':[{k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in mesh.items()} for mesh in meshes],
                 'materials':local_materials,'used_textures':[k for k,v in local_textures.items() if v['used']],
                 'missing_textures':sorted(local_report['missing_textures']),
                 'skipped_skinned_models':sorted(local_report.get('skipped_skinned_models',set())),
                 'degenerate_triangles_removed':local_report['degenerate_triangles_removed']}
        cache.put(key,entry)
    materials.update(entry['materials'])
    for key in entry['used_textures']: textures[key]['used'] = True
    report['missing_textures'].update(entry['missing_textures'])
    report['degenerate_triangles_removed'] += entry['degenerate_triangles_removed']
    if entry['skipped_skinned_models']: report.setdefault('skipped_skinned_models',set()).update(entry['skipped_skinned_models'])
    return [{k:np.asarray(v,dtype=int if k=='i' else float) if k in ('v','i','n','uv') and v is not None else v for k,v in mesh.items()} for mesh in entry['meshes']]
