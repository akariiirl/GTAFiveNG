"""Local CodeWalker XML -> BeamNG static geometry prototype. No game writes."""
from pathlib import Path
import argparse, collections, hashlib, json, math, shutil, zipfile, struct
import xml.etree.ElementTree as ET
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
NS = 'http://www.collada.org/2005/11/COLLADASchema'
ET.register_namespace('', NS)

def sub(parent, tag, text=None, **attrs):
    e = ET.SubElement(parent, '{'+NS+'}'+tag, {k:str(v) for k,v in attrs.items()})
    if text is not None: e.text = str(text)
    return e

def vec(e):
    return np.array([float(e.get(k, 0)) for k in 'xyz'])

def value(e, path, default=0):
    n=e.find(path)
    return float(n.get('value', default)) if n is not None else default

def normalized_dds(data):
    """Retain all complete BC mip levels; CodeWalker can export partial tail blocks."""
    if data[:4]!=b'DDS ' or len(data)<128: raise ValueError('Invalid DDS header')
    fourcc=data[84:88]
    if fourcc not in (b'DXT1',b'DXT3',b'DXT5'): return data,False
    height,width=struct.unpack_from('<II',data,12)
    count=max(1,struct.unpack_from('<I',data,28)[0]); block=8 if fourcc==b'DXT1' else 16
    used=0; complete=0
    for i in range(count):
        size=max(1,((width>>i)+3)//4)*max(1,((height>>i)+3)//4)*block
        if used+size>len(data)-128: break
        used+=size; complete+=1
    if not complete: raise ValueError('Truncated primary DDS image')
    if complete==count: return data,False
    fixed=bytearray(data[:128+used]); struct.pack_into('<I',fixed,28,complete)
    return bytes(fixed),True

def valid_mesh(v, indices):
    v=np.asarray(v, dtype=float); idx=np.asarray(indices, dtype=int).reshape(-1,3)
    if not np.isfinite(v).all(): raise ValueError('Nonfinite vertices')
    if len(idx) and (idx.min()<0 or idx.max()>=len(v)): raise ValueError('Invalid vertex indices')
    t=v[idx]
    good=np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1)>1e-9
    return idx[good], int((~good).sum())

def dae(path, meshes):
    root=ET.Element('{'+NS+'}COLLADA', version='1.4.1')
    asset=sub(root,'asset'); sub(asset,'created','2026-11-15T00:00:00Z'); sub(asset,'modified','2026-11-15T00:00:00Z')
    sub(asset,'unit', name='meter', meter='1'); sub(asset,'up_axis','Z_UP')
    effects=sub(root,'library_effects'); mats=sub(root,'library_materials')
    for name in sorted({m['material'] for m in meshes}):
        effect=sub(effects,'effect',id=name+'-fx'); profile=sub(effect,'profile_COMMON')
        tech=sub(profile,'technique',sid='common'); phong=sub(tech,'phong')
        sub(sub(phong,'diffuse'),'color','0.65 0.65 0.65 1')
        sub(sub(mats,'material',id=name,name=name),'instance_effect',url='#'+name+'-fx')
    library=sub(root,'library_geometries')
    scene=sub(sub(root,'library_visual_scenes'),'visual_scene',id='Scene',name='Scene')
    base=sub(scene,'node',id='base00',name='base00'); start=sub(base,'node',id='start01',name='start01')
    for k,m in enumerate(meshes):
        gid='geometry'+str(k); mesh=sub(sub(library,'geometry',id=gid,name=gid),'mesh')
        fields=[('positions',np.asarray(m['v']), 'XYZ')]
        if m.get('n') is not None: fields.append(('normals',np.asarray(m['n']),'XYZ'))
        if m.get('uv') is not None: fields.append(('uv',np.asarray(m['uv']),'ST'))
        for field,data,params in fields:
            sid=gid+'-'+field; source=sub(mesh,'source',id=sid)
            sub(source,'float_array',' '.join(format(float(x),'.8g') for x in data.flat),id=sid+'-array',count=data.size)
            access=sub(sub(source,'technique_common'),'accessor',source='#'+sid+'-array',count=len(data),stride=len(params))
            for p in params: sub(access,'param',name=p,type='float')
        sub(sub(mesh,'vertices',id=gid+'-vertices'),'input',semantic='POSITION',source='#'+gid+'-positions')
        tri=sub(mesh,'triangles',count=len(m['i']),material=m['material'])
        sub(tri,'input',semantic='VERTEX',source='#'+gid+'-vertices',offset=0)
        if m.get('n') is not None: sub(tri,'input',semantic='NORMAL',source='#'+gid+'-normals',offset=0)
        if m.get('uv') is not None: sub(tri,'input',semantic='TEXCOORD',source='#'+gid+'-uv',offset=0,set=0)
        sub(tri,'p',' '.join(str(int(x)) for x in np.asarray(m['i']).flat))
        node=sub(start,'node',id='node'+str(k),name=m.get('node','mesh'+str(k)+'_a100'))
        inst=sub(node,'instance_geometry',url='#'+gid)
        bind=sub(sub(inst,'bind_material'),'technique_common')
        sub(bind,'instance_material',symbol=m['material'],target='#'+m['material'])
    sub(sub(root,'scene'),'instance_visual_scene',url='#Scene')
    path.parent.mkdir(parents=True,exist_ok=True)
    ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)

def quat_matrix(e):
    # CEntityDef stores inverse rotation; CodeWalker YmapEntityDef inverts it.
    q=e.find('rotation'); x,y,z=-vec(q); w=float(q.get('w'))
    norm=math.sqrt(x*x+y*y+z*z+w*w)
    if norm<1e-8: raise ValueError('Zero quaternion')
    x,y,z,w=np.array([x,y,z,w])/norm
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])

def drawable(xml, name, materials, textures, report):
    root=ET.parse(xml).getroot(); shaders=root.findall('ShaderGroup/Shaders/Item')
    meshes=[]
    for k,g in enumerate(root.findall('DrawableModelsHigh/Item/Geometries/Item')):
        layout=list(g.find('VertexBuffer/Layout')); data=g.findtext('VertexBuffer/Data','').strip().splitlines()
        widths={'Position':3,'Normal':3,'Colour0':4,'Colour1':4,'Tangent':4,'BlendWeights':4,'BlendIndices':4}
        offsets={}; cursor=0
        for f in layout:
            n=widths.get(f.tag,2 if f.tag.startswith('TexCoord') else None)
            if n is None: raise ValueError('Unsupported vertex field '+f.tag)
            offsets[f.tag]=(cursor,cursor+n); cursor+=n
        a=np.array([[float(x) for x in line.split()] for line in data])
        if a.shape[1]!=cursor: raise ValueError('Vertex layout mismatch')
        v=a[:,slice(*offsets['Position'])]
        ix=np.fromstring(g.findtext('IndexBuffer/Data',''),sep=' ',dtype=int)
        idx,deg=valid_mesh(v,ix); report['degenerate_triangles_removed']+=deg
        si=int(value(g,'ShaderIndex')); shader=shaders[si]; mat='lsf_'+name+'_'+str(si)
        if mat not in materials:
            tex=shader.findtext("Parameters/Item[@name='DiffuseSampler']/Name")
            stage={'diffuseColor':[1,1,1,1],'specularPower':16,'useAnisotropic':True}
            if tex and tex.lower() in textures:
                target=tex.lower()+'.dds'; stage['diffuseMap']='/levels/los_santos_fazes/art/textures/'+target
                textures[tex.lower()]['used']=True
            elif tex: report['missing_textures'].add(tex)
            materials[mat]={'name':mat,'class':'Material','mapTo':mat,'Stages':[stage],'doubleSided':True}
            if any(s in shader.findtext('FileName','') for s in ('cutout','trees','foliage')):
                materials[mat].update(alphaTest=True,alphaRef=100)
            if shader.findtext('Name','')=='decal': materials[mat].update(translucent=True,translucentBlendOp='Lerp',translucentZWrite=False)
        normal=a[:,slice(*offsets['Normal'])] if 'Normal' in offsets else None
        uv=a[:,slice(*offsets['TexCoord0'])].copy() if 'TexCoord0' in offsets else None
        if uv is not None: uv[:,1]=1-uv[:,1]
        meshes.append({'v':v,'n':normal,'uv':uv,'i':idx,'material':mat})
    return meshes

def bounds_mesh(xml,origin,report):
    root=ET.parse(xml).getroot().find('Bounds'); meshes=[]
    def visit(b,parent):
        local=b.findtext('CompositeTransform')
        matrix=np.fromstring(local,sep=' ').reshape(4,4)@parent if local else parent
        if b.get('type')=='Composite':
            for child in b.findall('Children/Item'): visit(child,matrix)
            return
        raw=b.findtext('Vertices')
        if not raw:
            report['unsupported_collision'][b.get('type','unknown')]+=1; return
        v=np.array([[float(n) for n in row.strip().split(',')] for row in raw.strip().splitlines()])
        v+=vec(b.find('GeometryCenter'))
        v=(np.column_stack([v,np.ones(len(v))])@matrix)[:,:3]-origin
        ix=[]
        extra=[]
        for p in b.find('Polygons'):
            if p.tag=='Triangle': ix.append([int(p.get('v'+str(n))) for n in (1,2,3)])
            elif p.tag=='Box':
                # GTA stores four diagonal corners; formula matches CodeWalker Renderable.cs.
                p1,p2,p3,p4=[v[int(p.get('v'+str(n)))] for n in (1,2,3,4)]
                a=((p3+p4)-(p1+p2))*0.5
                edges=[a,p3-a-p1,p4-a-p1]
                corners=np.array([p1+i*edges[0]+j*edges[1]+k*edges[2] for i,j,k in [(0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1)]])
                faces=np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]])
                if np.linalg.det(np.array(edges))<0: faces=faces[:,::-1]
                start=len(v)+len(extra); extra.extend(corners); ix.extend(faces+start)
            else: report['unsupported_collision'][p.tag]+=1
        if extra: v=np.concatenate([v,np.array(extra)])
        if ix:
            idx,deg=valid_mesh(v,ix); report['degenerate_triangles_removed']+=deg
            meshes.append({'v':v,'i':idx,'material':'lsf_collision','node':'Colmesh-1'})
    visit(root,np.eye(4))
    # Single collision node avoids duplicate Colmesh names in a shape.
    if not meshes: return []
    verts=[]; indices=[]; offset=0
    for m in meshes:
        verts.extend(m['v']); indices.extend(m['i']+offset); offset+=len(m['v'])
    return [{'v':np.array(verts),'i':np.array(indices),'material':'lsf_collision','node':'Colmesh-1'}]

def jsonl(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(''.join(json.dumps(r,separators=(',',':'))+'\n' for r in rows))

def build(source,output,center,radius):
    origin=np.array([center[0],center[1],0.]); level=output/'levels/los_santos_fazes'
    level.mkdir(parents=True,exist_ok=True)
    report={'missing_assets':set(),'missing_textures':set(),'unsupported_collision':collections.Counter(),'degenerate_triangles_removed':0,'visual_instances':0,'collision_triangles':0,'visual_triangles':0,'source':'GTA V Legacy base archives','origin':origin.tolist(),'radius':radius,'in_game_verified':False}
    textures={p.stem.lower():{'path':p,'used':False} for p in sorted(source.glob('*.dds'))}
    drawables={p.name.split('.rpf_')[-1][:-8]:p for p in source.glob('*.ydr.xml')}
    materials={}; objects=[]; converted={}; used=set()
    for p in sorted(source.glob('*.ymap.xml')):
        if any(s in p.name for s in ('oldbill','newbill')): continue
        for e in ET.parse(p).getroot().findall('entities/Item'):
            if e.findtext('lodLevel') not in ('LODTYPES_DEPTH_HD','LODTYPES_DEPTH_ORPHANHD'): continue
            pos=vec(e.find('position')); name=e.findtext('archetypeName'); key=(name,*pos)
            if np.linalg.norm(pos[:2]-origin[:2])>radius or key in used: continue
            used.add(key)
            if name not in drawables: report['missing_assets'].add(name); continue
            if name not in converted:
                meshes=drawable(drawables[name],name,materials,textures,report)
                if not meshes: report['missing_assets'].add(name); continue
                dae(level/'art/shapes'/f'{name}.dae',meshes)
                converted[name]=sum(len(m['i']) for m in meshes)
            report['visual_triangles']+=converted[name]
            objects.append({'name':'lsf_visual_'+str(len(objects)),'class':'TSStatic','__parent':'Geometry','shapeName':'/levels/los_santos_fazes/art/shapes/'+name+'.dae','position':(pos-origin).tolist(),'rotationMatrix':quat_matrix(e).T.flatten().tolist(),'scale':[value(e,'scaleXY',1)]*2+[value(e,'scaleZ',1)],'collisionType':'None','decalType':'Visible Mesh','meshCulling':True})
            report['visual_instances']+=1
    for p in sorted(source.glob('*.ybn.xml')):
        # hi@ and base carry complementary collision, ma@ is weapon-only detail.
        if 'ma@' in p.name: continue
        b=ET.parse(p).getroot().find('Bounds'); lo=vec(b.find('BoxMin')); hi=vec(b.find('BoxMax'))
        if np.any(hi[:2]<origin[:2]-radius) or np.any(lo[:2]>origin[:2]+radius): continue
        meshes=bounds_mesh(p,origin,report)
        if not meshes: continue
        name='collision_'+hashlib.sha256(p.name.encode()).hexdigest()[:12]
        # Torque requires a nonnegative render detail even for a hidden physics shape.
        anchor=meshes[0]['v'][meshes[0]['i'][0]]
        render_detail={'v':anchor,'i':np.array([[0,1,2]]),'material':'lsf_collision','node':'anchor_a100'}
        dae(level/'art/shapes'/f'{name}.dae',[render_detail]+meshes)
        report['collision_triangles']+=sum(len(m['i']) for m in meshes)
        objects.append({'name':'lsf_'+name,'class':'TSStatic','__parent':'Geometry','shapeName':'/levels/los_santos_fazes/art/shapes/'+name+'.dae','position':[0,0,0],'collisionType':'Collision Mesh','decalType':'Collision Mesh','isRenderEnabled':False})
    materials['lsf_collision']={'name':'lsf_collision','class':'Material','mapTo':'lsf_collision','Stages':[{'diffuseColor':[0.5,0.5,0.5,1]}]}
    (level/'art/main.materials.json').write_text(json.dumps(materials,indent=2))
    td=level/'art/textures'; td.mkdir(exist_ok=True)
    report['dds_mip_headers_repaired']=0
    for name,tex in textures.items():
        if tex['used']:
            data,repaired=normalized_dds(tex['path'].read_bytes())
            (td/(name+'.dds')).write_bytes(data)
            report['dds_mip_headers_repaired']+=int(repaired)
    (level/'info.json').write_text(json.dumps({'title':'Los Santos — South Central prototype','description':'Local GTA V conversion. Partial region; unfinished edges and missing props.','authors':'Local conversion experiment','size':[radius*2,radius*2],'defaultSpawnPointName':'spawn_default','supportsTraffic':False},indent=2))
    jsonl(level/'main/items.level.json',[{'name':'MissionGroup','class':'SimGroup'}])
    jsonl(level/'main/MissionGroup/items.level.json',[{'name':n,'class':'SimGroup','__parent':'MissionGroup'} for n in ['Geometry','Sky','PlayerDropPoints']])
    jsonl(level/'main/MissionGroup/Geometry/items.level.json',objects)
    jsonl(level/'main/MissionGroup/PlayerDropPoints/items.level.json',[{'name':'spawn_default','class':'SpawnSphere','__parent':'PlayerDropPoints','position':[100,50,31],'radius':5,'dataBlock':'SpawnSphereMarker'}])
    jsonl(level/'main/MissionGroup/Sky/items.level.json',[{'name':'theLevelInfo','class':'LevelInfo','__parent':'Sky','globalEnviromentMap':'BNG_Sky_01_cubemap','gravity':-9.81,'visibleDistance':2500,'fogDensity':0.0001}, {'name':'sunsky','class':'ScatterSky','__parent':'Sky','skyBrightness':40,'azimuth':90,'elevation':45}, {'name':'tod','class':'TimeOfDay','__parent':'Sky','time':0.15,'play':False}])
    for k in ['missing_assets','missing_textures']: report[k]=sorted(report[k])
    report['textures']=sum(t['used'] for t in textures.values()); report['unique_drawables']=len(converted)
    (output/'conversion_report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in ('missing_assets','missing_textures')},indent=2))
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--source',type=Path,default=ROOT/'generated/source'); parser.add_argument('--output',type=Path,default=ROOT/'generated/prototype'); parser.add_argument('--center',nargs=2,type=float,default=[-370,-1330]); parser.add_argument('--radius',type=float,default=220)
    args=parser.parse_args(); build(args.source,args.output,args.center,args.radius)
