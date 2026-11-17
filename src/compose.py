"""Experimental offline composition of validated converter builds into one level."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
import numpy as np
from convert import NS, jsonl
from package import validate, package
from planning import chunk_id
from region import fingerprints
from selection import frame

LEVEL='levels/los_santos_fazes'
# Converter instances of the same YBN may differ by float formatting after
# origin translation. Two positions may merge only within this absolute error.
COLLISION_VERTEX_TOLERANCE_M=2e-5


def collision_geometry(root):
    """Return exact non-position XML and ordered world-space position arrays.

    The XML includes triangle indices/winding, material bindings, geometry and
    node structure. Clearing position text only for the fingerprint keeps
    topology checks exact while permitting sub-millimetre coordinate noise.
    """
    arrays=[]; saved=[]
    for node in root.findall('.//{*}source'):
        if not node.get('id','').endswith('-positions'): continue
        values=node.find('{*}float_array')
        if values is None or values.text is None: raise ValueError('Collision positions missing')
        array=np.fromstring(values.text,sep=' ')
        if len(array)%3 or not np.isfinite(array).all(): raise ValueError('Invalid collision positions')
        arrays.append(array)
        saved.append((values,values.text)); values.text='__world_positions__'
    if not arrays: raise ValueError('Collision geometry has no positions')
    try: structure=hashlib.sha256(ET.tostring(root,encoding='utf-8')).digest()
    finally:
        for node,value in saved: node.text=value
    return structure,arrays


def collision_equivalent(left,right,tolerance=COLLISION_VERTEX_TOLERANCE_M):
    if left[0]!=right[0] or len(left[1])!=len(right[1]): return False
    return all(a.shape==b.shape and np.allclose(a,b,rtol=0,atol=tolerance)
               for a,b in zip(left[1],right[1]))


def collision_group(obj, source):
    provenance=obj.get('sourceArchetype',source.stem)
    # All object properties except transient name/path and validated zero
    # position must agree, in addition to source identity and mesh geometry.
    properties=digest({k:v for k,v in obj.items() if k not in ('name','shapeName','position','sourceArchetype')})
    return provenance,properties

def core_outputs(output):
    return {k:v for k,v in fingerprints(output).items() if k.startswith('levels/') or k in ('conversion_report.json','chunks.json','composed.zip','composed.manifest.json')}



def digest(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def compose(builds, output, origin=None):
    output=Path(output).resolve()
    inputs=[]
    for build in builds:
        build=Path(build).resolve()
        if output==build or output in build.parents or build in output.parents: raise ValueError('Composition output must be separate')
        validate(build)
        report=json.loads((build/'conversion_report.json').read_text())
        fingerprint=fingerprints(build/LEVEL)
        inputs.append((digest({'report':report,'files':fingerprint}),build,report,fingerprint))
    inputs=sorted({item[0]:item for item in inputs}.values(),key=lambda item:item[0])
    if not inputs: raise ValueError('At least one build required')
    origin=np.asarray(origin if origin is not None else np.min([item[2]['origin'] for item in inputs],axis=0),dtype=float)
    if origin.shape!=(3,) or not np.isfinite(origin).all(): raise ValueError('Finite XYZ origin required')
    signature={'inputs':[item[0] for item in inputs],'origin':origin.tolist(),
               'pipeline':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}}
    manifest=output/'composition-manifest.json'
    if manifest.exists():
        previous=json.loads(manifest.read_text())
        actual=core_outputs(output)
        if previous['signature']!=signature or previous['outputs']!=actual: raise ValueError('Changed composition preserved')
        validate(output); return output
    if output.exists(): raise FileExistsError('Incomplete composition preserved; use a fresh output')
    output.mkdir(parents=True)
    level=output/LEVEL; first=inputs[0][1]/LEVEL
    shutil.copytree(first,level,ignore=shutil.ignore_patterns('art'))
    (level/'art/shapes').mkdir(parents=True); (level/'art/textures').mkdir()
    materials={}; objects={}; chunks={}; selections=[]; missing_assets=set(); missing_textures=set()
    collision_sources={}; collision_deduplicated=0; collision_nonmatching=0
    for input_id,build,report,fingerprint in inputs:
        offset=np.array(report['origin'])-origin
        selections.append(report.get('selection',{'center':report['origin'][:2],'radius':report['radius']}))
        missing_assets.update(report.get('missing_assets',[])); missing_textures.update(report.get('missing_textures',[]))
        local_materials={}
        for path in sorted((build/LEVEL).rglob('*.materials.json')): local_materials.update(json.loads(path.read_text()))
        bindings={}
        for old,material in sorted(local_materials.items()):
            material=json.loads(json.dumps(material))
            for stage in material.get('Stages',[]):
                for key,value in list(stage.items()):
                    if key.endswith('Map') and isinstance(value,str) and value.startswith('/levels/'):
                        source=(build/value.lstrip('/')).resolve()
                        if build not in source.parents: raise ValueError('Texture path escapes build')
                        data=source.read_bytes(); name=hashlib.sha256(data).hexdigest()+source.suffix
                        target=level/'art/textures'/name
                        if not target.exists(): target.write_bytes(data)
                        stage[key]='/'+LEVEL+'/art/textures/'+name
            material.pop('name',None); material.pop('mapTo',None)
            name='lsf_m_'+digest(material); bindings[old]=name
            materials[name]={'name':name,'mapTo':name,**material}
        shape_paths={}
        geometry=build/LEVEL/'main/MissionGroup/Geometry/items.level.json'
        for line in geometry.read_text().splitlines():
            if not line.strip(): continue
            obj=json.loads(line); collision=obj.get('collisionType')=='Collision Mesh'
            if collision and (np.any(np.array(obj.get('position',[0,0,0]))!=0) or np.any(np.array(obj.get('scale',[1,1,1]))!=1) or not np.allclose(np.array(obj.get('rotationMatrix',np.eye(3).flatten())).reshape(3,3),np.eye(3))): raise ValueError('Unsupported nonidentity collision object transform')
            source=(build/obj['shapeName'].lstrip('/')).resolve()
            if build not in source.parents: raise ValueError('Shape path escapes build')
            cache_key=(str(source),collision)
            if cache_key not in shape_paths:
                tree=ET.parse(source); root=tree.getroot()
                for element in root.iter():
                    for key,value in list(element.attrib.items()):
                        prefix='#' if value.startswith('#') else ''; token=value.lstrip('#')
                        if token in bindings: element.set(key,prefix+bindings[token])
                        elif token.endswith('-fx') and token[:-3] in bindings: element.set(key,prefix+bindings[token[:-3]]+'-fx')
                if collision:
                    for node in root.findall('.//{*}source'):
                        if not node.get('id','').endswith('-positions'): continue
                        array=node.find('{*}float_array'); values=np.fromstring(array.text,sep=' ').reshape(-1,3)+offset
                        array.text=' '.join(format(float(v),'.17g') for v in values.flat)
                equivalent_path=None
                if collision:
                    # Source stem encodes the exact exported resource filename;
                    # never merge across different archive-path provenance.
                    group=collision_group(obj,source)
                    geometry=collision_geometry(root)
                    for candidate_path in collision_sources.get(group,[]):
                        # Re-read the canonical shape instead of retaining every
                        # GTA collision vertex array in process memory.
                        candidate_geometry=collision_geometry(ET.parse(output/candidate_path.lstrip('/')).getroot())
                        if collision_equivalent(geometry,candidate_geometry):
                            equivalent_path=candidate_path; collision_deduplicated+=1; break
                    if equivalent_path is None and group in collision_sources: collision_nonmatching+=1
                if equivalent_path is not None:
                    shape_paths[cache_key]=equivalent_path
                else:
                    data=ET.tostring(root,encoding='utf-8',xml_declaration=True)
                    prefix='collision_' if collision else 'sc1_rd_r_' if source.stem.startswith('sc1_rd_r') else 'shape_'
                    name=prefix+hashlib.sha256(data).hexdigest()+'.dae'
                    target=level/'art/shapes'/name
                    if not target.exists(): target.write_bytes(data)
                    shape_paths[cache_key]='/'+LEVEL+'/art/shapes/'+name
                    if collision: collision_sources.setdefault(group,[]).append(shape_paths[cache_key])
            obj['shapeName']=shape_paths[cache_key]
            obj['sourceArchetype']=obj.get('sourceArchetype',source.stem)
            if collision: obj['position']=[0,0,0]
            else: obj['position']=(np.array(obj['position'])+offset).tolist()
            obj.pop('name',None); obj['__parent']='Geometry'
            # Nanometre rounding only stabilizes duplicate identity, never output coordinates.
            identity=json.loads(json.dumps(obj)); identity['position']=[round(v,9) for v in obj['position']]
            if collision: identity.pop('sourceArchetype',None)
            key=digest(identity); obj['name']='composed_'+key
            objects.setdefault(key,obj)
            tree=ET.parse(output/obj['shapeName'].lstrip('/'))
            arrays=[np.fromstring(node.find('{*}float_array').text,sep=' ').reshape(-1,3) for node in tree.findall('.//{*}source') if node.get('id','').endswith('-positions')]
            vertices=np.concatenate(arrays)
            if not collision: vertices=(vertices*np.array(obj.get('scale',[1,1,1])))@np.array(obj.get('rotationMatrix',np.eye(3).flatten())).reshape(3,3)+obj['position']
            vertices+=origin
            low=np.floor(vertices[:,:2].min(axis=0)/256).astype(int); high=np.floor(vertices[:,:2].max(axis=0)/256).astype(int)
            if int(np.prod(high-low+1))>100000: raise ValueError('Object spans excessive chunk grid')
            for x in range(low[0],high[0]+1):
                for y in range(low[1],high[1]+1):
                    chunk=chunks.setdefault(f'{x}_{y}',{'objects':set(),'inputs':set()})
                    chunk['objects'].add(obj['name']); chunk['inputs'].add(input_id)
        if fingerprints(build/LEVEL)!=fingerprint: raise ValueError('Input changed during composition')
    (level/'art/main.materials.json').write_text(json.dumps(materials,sort_keys=True,indent=2))
    jsonl(level/'main/MissionGroup/Geometry/items.level.json',[objects[k] for k in sorted(objects)])
    # Keep the first input spawn in its original world coordinates.
    spawn=level/'main/MissionGroup/PlayerDropPoints/items.level.json'
    if spawn.exists():
        rows=[json.loads(line) for line in spawn.read_text().splitlines() if line.strip()]
        offset=np.array(inputs[0][2]['origin'])-origin
        for row in rows:
            if 'position' in row: row['position']=(np.array(row['position'])+offset).tolist()
        jsonl(spawn,rows)
    visual_count=collision_count=0
    for obj in objects.values():
        tree=ET.parse(output/obj['shapeName'].lstrip('/'))
        if obj.get('collisionType')=='Collision Mesh':
            ids={n.find('{*}instance_geometry').get('url')[1:] for n in tree.findall('.//{*}node') if n.get('name','').startswith('Colmesh') and n.find('{*}instance_geometry') is not None}
            collision_count+=sum(int(t.get('count')) for g in tree.findall('.//{*}geometry') if g.get('id') in ids for t in g.findall('.//{*}triangles'))
        else: visual_count+=sum(int(t.get('count')) for t in tree.findall('.//{*}triangles'))
    boxes=[]
    for config in selections:
        center,radius,size=frame(config); boxes.append([center[0]-size[0]/2,center[1]-size[1]/2,center[0]+size[0]/2,center[1]+size[1]/2])
    lo=np.min(np.array(boxes)[:,:2],axis=0); hi=np.max(np.array(boxes)[:,2:],axis=0)
    info=json.loads((level/'info.json').read_text()); info.update(title='Los Santos experimental composed region',size=(hi-lo).tolist())
    (level/'info.json').write_text(json.dumps(info,sort_keys=True,indent=2))
    report={'origin':origin.tolist(),'selection':{'regions':sorted(selections,key=lambda x:json.dumps(x,sort_keys=True))},'radius':float(np.linalg.norm(hi-lo)/2),
            'visual_instances':sum(o.get('collisionType')=='None' for o in objects.values()),'unique_drawables':len({o['shapeName'] for o in objects.values() if o.get('collisionType')=='None'}),
            'visual_triangles':visual_count,'collision_triangles':collision_count,'collision_deduplicated_instances':collision_deduplicated,
            'collision_same_provenance_nonmatching_instances':collision_nonmatching,'collision_vertex_tolerance_m':COLLISION_VERTEX_TOLERANCE_M,
            'missing_assets':sorted(missing_assets),'missing_textures':sorted(missing_textures),'in_game_verified':False}
    (output/'conversion_report.json').write_text(json.dumps(report,sort_keys=True,indent=2))
    (output/'chunks.json').write_text(json.dumps({k:{field:sorted(value) for field,value in record.items()} for k,record in sorted(chunks.items())},sort_keys=True,indent=2))
    validate(output); package(output,output/'composed.zip')
    manifest.write_text(json.dumps({'signature':signature,'outputs':core_outputs(output),'in_game_verified':False},sort_keys=True,indent=2))
    return output


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('builds',nargs='+',type=Path); p.add_argument('--output',required=True,type=Path); p.add_argument('--origin',nargs=3,type=float)
    a=p.parse_args(); print(compose(a.builds,a.output,a.origin))
