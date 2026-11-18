"""Upgrade layered GTA ground materials in a preserved streamed level ZIP.

Only active, unambiguous YDR exports and their scoped texture bindings are
used. Scene placement, source vertices, collision and streaming manifests are
copied byte-for-byte from the known-good package.
"""
import argparse
import collections
import copy
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

import numpy as np

from convert import NS, normalized_dds, valid_mesh
from dependencies import TextureCatalog
from terrain import is_layered_terrain, triangle_layers
from resource_cache import hash_file

LEVEL = 'levels/los_santos_fazes/'


def source_names(folder):
    result=collections.defaultdict(list)
    for path in folder.glob('*.ydr.xml'):
        name=path.name.split('.rpf_',1)[-1].removesuffix('.ydr.xml').lower()
        result[name].append(path)
    return result


def terrain_geometry(geometry, shader):
    layout=[x.tag for x in geometry.find('VertexBuffer/Layout')]
    if 'Colour1' not in layout or 'TexCoord0' not in layout: return None
    lines=[x for x in geometry.findtext('VertexBuffer/Data','').splitlines() if x.strip()]
    if not lines: return None
    groups=re.split(r'\s{2,}',lines[0].strip())
    if len(groups)!=len(layout): return None
    widths=dict(zip(layout,(len(g.split()) for g in groups)))
    start=sum(widths[n] for n in layout[:layout.index('Colour1')])
    colour=np.array([[float(v) for v in line.split()[start:start+4]] for line in lines])
    positions_start=sum(widths[n] for n in layout[:layout.index('Position')])
    positions=np.array([[float(v) for v in line.split()[positions_start:positions_start+3]] for line in lines])
    indices=np.fromstring(geometry.findtext('IndexBuffer/Data',''),sep=' ',dtype=int)
    faces,_=valid_mesh(positions,indices)
    layers=[shader.findtext("Parameters/Item[@name='TextureSampler_layer%d']/Name" % k) for k in range(4)]
    if not all(layers): return None
    return faces,triangle_layers(colour,faces),layers


def add_material(root, name):
    effects=root.find('{*}library_effects'); mats=root.find('{*}library_materials')
    effect=ET.SubElement(effects,'{'+NS+'}effect',id=name+'-fx')
    profile=ET.SubElement(effect,'{'+NS+'}profile_COMMON')
    technique=ET.SubElement(profile,'{'+NS+'}technique',sid='common')
    phong=ET.SubElement(technique,'{'+NS+'}phong')
    diffuse=ET.SubElement(phong,'{'+NS+'}diffuse')
    ET.SubElement(diffuse,'{'+NS+'}color').text='0.65 0.65 0.65 1'
    material=ET.SubElement(mats,'{'+NS+'}material',id=name,name=name)
    ET.SubElement(material,'{'+NS+'}instance_effect',url='#'+name+'-fx')


def patch_shape(data, source, binding, materials, textures, missing):
    original=ET.fromstring(data); ydr=ET.parse(source).getroot()
    geometries=ydr.findall('DrawableModelsHigh/Item/Geometries/Item')
    shapes=original.findall('.//{*}library_geometries/{*}geometry')
    if len(geometries)!=len(shapes): return None,0,'geometry_count_mismatch'
    shaders=ydr.findall('ShaderGroup/Shaders/Item')
    changed=0
    for index,(geometry,shape) in enumerate(zip(geometries,shapes)):
        shader=shaders[int(float(geometry.find('ShaderIndex').get('value')))]
        if not is_layered_terrain(shader.findtext('FileName','').lower()): continue
        mesh=shape.find('{*}mesh'); old=mesh.find('{*}triangles')
        terrain=terrain_geometry(geometry,shader)
        if terrain is None or old is None: missing.add('unsupported_shader_or_vertex_layout'); continue
        faces,layers,names=terrain
        if len(faces)!=int(old.get('count')) or not np.array_equal(faces,np.fromstring(old.findtext('{*}p'),sep=' ',dtype=int).reshape(-1,3)):
            missing.add('triangle_topology_mismatch'); continue
        resolved={}
        for layer in set(layers):
            name=names[int(layer)].lower()
            if name not in binding:
                missing.add('unresolved_texture:'+name); continue
            path=binding[name]['path']; raw,_=normalized_dds(path.read_bytes())
            target=hashlib.sha256(raw).hexdigest()+'.dds'
            resolved[layer]=('lsf_terrain_'+hashlib.sha256(raw).hexdigest(),target,raw)
        if set(layers)!=set(resolved): continue
        node=original.find(".//{*}node[@id='node%d']" % index)
        if node is None: missing.add('missing_shape_node'); continue
        bindings=node.find('.//{*}technique_common')
        original_index=list(mesh).index(old); mesh.remove(old)
        for layer in sorted(resolved):
            material,target,raw=resolved[layer]
            picked=faces[layers==layer]
            tri=copy.deepcopy(old); tri.set('material',material); tri.set('count',str(len(picked)))
            tri.find('{*}p').text=' '.join(str(int(x)) for x in picked.flat)
            mesh.insert(original_index,tri); original_index+=1
            if material not in materials:
                materials[material]={'name':material,'class':'Material','mapTo':material,'Stages':[{'diffuseColor':[1,1,1,1],'specularPower':16,'useAnisotropic':True,'diffuseMap':'/'+LEVEL+'art/textures/'+target}],'doubleSided':True}
                add_material(original,material)
            if target not in textures: textures[target]=raw
            ET.SubElement(bindings,'{'+NS+'}instance_material',symbol=material,target='#'+material)
        changed+=len(faces)
    if not changed: return None,0,None
    return ET.tostring(original,encoding='utf-8',xml_declaration=True),changed,None


def build(source_zip, output_zip, shared_xml, cells_root, report_path):
    source_zip,output_zip,report_path=Path(source_zip),Path(output_zip),Path(report_path)
    temporary=output_zip.with_name(output_zip.name+'.partial')
    if output_zip.exists() or temporary.exists() or report_path.exists(): raise FileExistsError('Preserving existing terrain build')
    sources=source_names(Path(shared_xml))
    cell_root=Path(cells_root)
    prepared=sorted(set().union(*(set(cell_root.glob(pattern)) for pattern in (
        'tech_*/cell/prepared-000','tech_*/prepared-000',
        '*/tech_*/cell/prepared-000','*/tech_*/prepared-000'))))
    source_dirs=collections.defaultdict(list)
    for folder in prepared:
        for name,paths in source_names(folder).items():
            source_dirs[name].extend(paths)
    catalogs={}; replacements={}; textures={}; materials={}; missing=set(); stats=collections.Counter()
    with zipfile.ZipFile(source_zip) as original:
        rows=[]
        for item in original.namelist():
            if item.startswith(LEVEL+'stream/cells/') and item.endswith('.json'):
                rows.extend(json.loads(original.read(item)))
        if not rows: raise ValueError('No streamed cell objects in source package')
        material_path=LEVEL+'art/main.materials.json'
        materials=json.loads(original.read(material_path))
        shapes={r['shapeName'].lstrip('/'):r['sourceArchetype'].lower() for r in rows if r.get('collisionType')=='None' and 'sourceArchetype' in r}
        for shape,name in sorted(shapes.items()):
            candidates=sources.get(name,[])
            if not candidates: continue
            if not any(b'terrain_cb' in p.read_bytes() for p in candidates): continue
            hashes={hash_file(p) for p in candidates}
            if len(hashes)!=1: missing.add('conflicting_source:'+name); continue
            source=candidates[0]
            matching=[p for p in source_dirs.get(name,[]) if hash_file(p) in hashes]
            if not matching: missing.add('no_matching_prepared_source:'+name); continue
            ydr=ET.parse(source).getroot()
            required={item.findtext('Name','').lower() for shader in ydr.findall('ShaderGroup/Shaders/Item')
                      if is_layered_terrain(shader.findtext('FileName','').lower())
                      for item in shader.findall('Parameters/Item') if item.get('name','').startswith('TextureSampler_layer')}
            signatures=set(); binding=None
            for path in matching:
                folder=path.parent
                if folder not in catalogs: catalogs[folder]=TextureCatalog(folder)
                candidate=catalogs[folder].for_asset(name)
                signatures.add(tuple((key,hash_file(candidate[key]['path']) if key in candidate else None) for key in sorted(required)))
                binding=candidate
            if len(signatures)!=1: missing.add('conflicting_scoped_texture:'+name); continue
            patched,count,error=patch_shape(original.read(shape),source,binding,materials,textures,missing)
            if error: missing.add(error+':'+name)
            if patched is not None:
                replacements[shape]=patched; stats['terrain_triangles_textured']+=count; stats['terrain_shapes_textured']+=1
        if not stats['terrain_shapes_textured']: raise ValueError('No resolved layered terrain; existing package preserved')
        replacements[material_path]=json.dumps(materials,sort_keys=True,indent=2).encode()
        for name,data in textures.items(): replacements[LEVEL+'art/textures/'+name]=data
        output_zip.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as output:
            for item in original.infolist():
                info=zipfile.ZipInfo(item.filename,date_time=(2026,11,17,0,0,0))
                info.compress_type=zipfile.ZIP_DEFLATED
                info.external_attr=item.external_attr
                if item.is_dir(): output.writestr(info,b''); continue
                if item.filename in replacements:
                    output.writestr(info,replacements.pop(item.filename)); stats['files_replaced']+=1
                else:
                    with original.open(item) as stream, output.open(info,'w',force_zip64=True) as target:
                        for block in iter(lambda:stream.read(1024*1024),b''): target.write(block)
            for name,data in sorted(replacements.items()):
                info=zipfile.ZipInfo(name,date_time=(2026,11,17,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED
                output.writestr(info,data)
    temporary.rename(output_zip)
    report={'source_zip':str(source_zip),'output_zip':str(output_zip),'source_sha256':hash_file(source_zip),
            'output_sha256':hash_file(output_zip),'output_bytes':output_zip.stat().st_size,
            'prepared_cells':len(prepared),'source_shapes':len(shapes),'stats':dict(stats),'new_textures':len(textures),
            'unresolved':sorted(missing),'in_game_verified':False,'method':'Original GTA triangle colour weights select one source layer per triangle; full four-layer blending is not reproduced.'}
    report_path.write_text(json.dumps(report,sort_keys=True,indent=2))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_zip',type=Path); parser.add_argument('output_zip',type=Path)
    parser.add_argument('--shared-xml',required=True,type=Path); parser.add_argument('--cells-root',required=True,type=Path)
    parser.add_argument('--report',required=True,type=Path)
    args=parser.parse_args(); print(json.dumps(build(args.source_zip,args.output_zip,args.shared_xml,args.cells_root,args.report),indent=2))
