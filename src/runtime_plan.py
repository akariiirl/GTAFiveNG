"""Export isolated experimental prefab assets/plans, never alter the composed level."""
import argparse
import json
from pathlib import Path
import shutil
from compose import LEVEL
from package import validate
from resource_cache import hash_file


def export_runtime_plan(build, output, max_chunks=4, max_bytes=512*1024*1024):
    build=Path(build).resolve(); output=Path(output).resolve()
    if output==build or output in build.parents or build in output.parents: raise ValueError('Runtime experiment must be separate')
    if max_chunks<1 or max_bytes<0: raise ValueError('Invalid runtime plan budgets')
    validate(build)
    if output.exists(): raise FileExistsError('Preserving existing runtime experiment')
    objects={o['name']:o for o in (json.loads(line) for line in (build/LEVEL/'main/MissionGroup/Geometry/items.level.json').read_text().splitlines() if line.strip())}
    chunks=json.loads((build/'chunks.json').read_text()); membership={}
    for key,record in sorted(chunks.items()):
        for name in record['objects']:
            if name not in objects: raise ValueError('Chunk references missing object')
            membership.setdefault(name,[]).append(key)
    if set(membership)!=set(objects): raise ValueError('Chunk membership incomplete')
    owners={name:min(keys) for name,keys in membership.items()}
    output.mkdir(parents=True)
    shutil.copytree(build/LEVEL/'art',output/LEVEL/'art')
    folder=output/LEVEL/'experimental/chunks'; folder.mkdir(parents=True)
    result={'origin':json.loads((build/'conversion_report.json').read_text())['origin'],'coordinates':'Prefab positions use level coordinates; chunk IDs use original GTA XY', 'schema':1,'experimental':True,'in_game_verified':False,'max_active_chunks':max_chunks,'max_estimated_bytes':max_bytes,'chunks':{},
            'limitations':['File sizes and Lua heap are not engine/GPU memory.','Use a separate empty-scene profile; do not load on top of the normal composed scene.','Scene bindings, collision activation and unload/reload are unverified in BeamNG.']}
    shared=list((output/LEVEL/'art').rglob('*.dds'))+list((output/LEVEL/'art').rglob('*.materials.json'))
    for key,record in sorted(chunks.items()):
        group='chunk_'+key.replace('-','m'); rows=[{'class':'SimGroup','name':group,'noAutoReload':True}]
        own=[name for name in sorted(record['objects']) if owners[name]==key]
        for name in own:
            obj={**objects[name]}; obj.pop('__parent',None); obj['name']='runtime_'+name; rows.append(obj)
        path=folder/(key+'.prefab.json'); path.write_text(''.join(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n' for row in rows))
        resources={output/objects[name]['shapeName'].lstrip('/') for name in own}
        estimated=path.stat().st_size+sum(p.stat().st_size for p in resources|set(shared))
        result['chunks'][key]={'filename':'/'+path.relative_to(output).as_posix(),'sha256':hash_file(path),'estimated_bytes':estimated,
                               'dependencies':sorted({owners[name] for name in record['objects'] if owners[name]!=key}),'owned_objects':own}
    extension=output/'lua/ge/extensions/lsf/chunkPrototype.lua'; extension.parent.mkdir(parents=True)
    shutil.copyfile(Path(__file__).with_name('chunk_prototype.lua'),extension)
    manifest=output/'runtime-plan.json'; manifest.write_text(json.dumps(result,sort_keys=True,indent=2))
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('build',type=Path); p.add_argument('--output',required=True,type=Path)
    p.add_argument('--max-chunks',type=int,default=4); p.add_argument('--max-bytes',type=int,default=512*1024*1024)
    a=p.parse_args(); print(export_runtime_plan(a.build,a.output,a.max_chunks,a.max_bytes))
