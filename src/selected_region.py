"""Plan an explicitly CodeWalker-selected prototype from existing catalog evidence."""
import argparse
from collections import Counter,defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import numpy as np
from convert import quat_matrix,vec,value
from dependencies import joaat
from extraction import export_name
from local_workflow import safe_metadata


def norm(path): return path.lower().replace('\\','/')
def name_hash(name):
    match=re.fullmatch(r'hash_([0-9a-fA-F]{8})',name)
    return int(match[1],16) if match else joaat(name)


def placement_bounds(item, archetype):
    lo,hi=archetype.find('bbMin'),archetype.find('bbMax')
    if lo is None or hi is None: raise ValueError('Archetype bounds unavailable')
    lo,hi=vec(lo),vec(hi)
    corners=np.array([[x,y,z] for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])])
    corners=(corners*np.array([value(item,'scaleXY',1)]*2+[value(item,'scaleZ',1)]))@quat_matrix(item).T+vec(item.find('position'))
    return np.r_[corners[:,:2].min(axis=0),corners[:,:2].max(axis=0)]

def overlaps_placement(item, archetype, box):
    b=placement_bounds(item,archetype)
    return bool(np.all(b[2:]>=box[:2]) and np.all(b[:2]<=box[2:]))

def plan(root, output, evidence_file='codewalker-selection-01.json', bbox=None):
    evidence=json.loads((root/evidence_file).read_text())
    snapshot=Path(json.loads((root/'catalog/bootstrap.json').read_text())['snapshot'])
    records={r['path']:r for r in map(json.loads,(snapshot/'inventory.jsonl').read_text().splitlines())}
    maps=[norm(p) for p in evidence['ymap'].values() if any(x in p.lower() for x in ('scentral','koreatown','downtown_01'))]
    def read(path):
        r=records[path]; data=(snapshot/r['xml']).read_bytes()
        if hashlib.sha256(data).hexdigest()!=r['xml_sha256']: raise ValueError('Changed metadata: '+path)
        return ET.fromstring(safe_metadata(data))
    def placements(path):
        result=[]
        for index,item in enumerate(read(path).findall('entities/Item')):
            if item.findtext('lodLevel') not in ('LODTYPES_DEPTH_HD','LODTYPES_DEPTH_ORPHANHD'): continue
            pos=item.find('position'); xyz=[float(pos.get(k)) for k in 'xyz']
            if -850<=xyz[0]<=450 and -2000<=xyz[1]<=-900:
                result.append({'map':path,'index':index,'name':item.findtext('archetypeName'),'position':xyz,'xml':ET.tostring(item,encoding='unicode')})
        return result
    with ThreadPoolExecutor(max_workers=4) as pool: placed=[p for batch in pool.map(placements,maps) for p in batch]
    cells=defaultdict(list)
    for p in placed: cells[int(p['position'][0]//100),int(p['position'][1]//100)].append(p)
    typecache={}
    def archetype(name):
        path=evidence['archetypes'].get(str(name_hash(name)))
        if not path: return None,None
        path=norm(path)
        if path not in typecache:
            typecache[path]={name_hash(i.findtext('name','')):i for i in read(path).findall('.//archetypes/Item') if i.findtext('name')}
        return path,typecache[path].get(name_hash(name))
    summaries=[]; plans={}
    if bbox is not None:
        from selection import selection
        selection(bbox=bbox)
        included=[]
        for p in placed:
            _,a=archetype(p['name'])
            if a is None:
                if bbox[0]<=p['position'][0]<=bbox[2] and bbox[1]<=p['position'][1]<=bbox[3]:
                    raise ValueError('Required archetype missing: '+p['name'])
                continue
            if overlaps_placement(ET.fromstring(p['xml']),a,bbox): included.append(p)
        cells={(0,0):included}
    for cell,items in sorted(cells.items()):
        if bbox is None and not 15<=len(items)<=800: continue
        paths=set(); missing=[]; txds={}; road=0; embedded=[]; parents={}; nonvisual=[]; visual_bounds=[]
        for p in items:
            paths.add(p['map']); typ,a=archetype(p['name'])
            if a is None: missing.append('archetype:'+p['name']); continue
            paths.add(typ); name=a.findtext('name'); asset=a.findtext('assetName',name); kind=a.findtext('assetType')
            if kind=='ASSET_TYPE_ASSETLESS':nonvisual.append(name);continue
            visual_bounds.append(placement_bounds(ET.fromstring(p['xml']),a))
            ext={'ASSET_TYPE_DRAWABLE':'ydr','ASSET_TYPE_DRAWABLEDICTIONARY':'ydd','ASSET_TYPE_FRAGMENT':'yft'}.get(kind)
            if not ext: missing.append('asset type:'+str(kind)); continue
            key=a.findtext('drawableDictionary') if ext=='ydd' else asset
            if not key or key=='hash_00000000': key=asset
            visual=evidence[ext].get(str(name_hash(key)))
            if visual: paths.add(norm(visual))
            else: missing.append(ext+':'+key)
            if not name.startswith('prop_') and re.search(r'_rd_r\d|_road',name): road+=1
            txd=a.findtext('textureDictionary','')
            if txd and txd!='hash_00000000':
                h=str(name_hash(txd)); seen=set(); previous=None
                while h and h not in seen:
                    seen.add(h); texture=evidence['ytd'].get(h)
                    dictionary=Path(norm(texture)).stem if texture else 'hash_%08x'%int(h)
                    if previous: parents[previous]=dictionary
                    else: txds[name]=dictionary
                    if texture: paths.add(norm(texture))
                    else: embedded.append(dictionary)
                    previous=dictionary; h=evidence.get('textureParents',{}).get(h)
                if h:missing.append('texture parent cycle:'+txd)
        box=bbox if bbox is not None else [cell[0]*100,cell[1]*100,(cell[0]+1)*100,(cell[1]+1)*100]
        coverage=np.array(visual_bounds+[box]);collision_box=np.r_[coverage[:,:2].min(axis=0),coverage[:,2:].max(axis=0)]
        collision=[]
        for path in evidence['ybn'].values():
            path=norm(path); r=records.get(path); b=r.get('bounds_xy') if r else None
            if b and b[0]<=collision_box[2] and b[2]>=collision_box[0] and b[1]<=collision_box[3] and b[3]>=collision_box[1] and not r['name'].startswith('ma@'):
                collision.append(path)
        paths.update(collision)
        summary={'cell':list(cell),'bbox':box,'collision_bbox':collision_box.tolist(),'nonvisual_assetless':nonvisual,'hd_placements':len(items),'road_placements':road,'resource_tasks':len(paths),'collision_resources':len(collision),'missing':sorted(set(missing)),'embedded_txd_verification_pending':sorted(set(embedded))}
        summaries.append(summary); plans[cell]=(paths,txds,items,parents)
    valid=[x for x in summaries if not x['missing'] and x['road_placements'] and x['collision_resources']]
    if not valid: raise ValueError('No resolvable nonempty road region: '+json.dumps(summaries))
    selected=min(valid,key=lambda x:(abs(x['cell'][0]+4)+abs(x['cell'][1]+14),x['resource_tasks']))
    paths,txds,items,parents=plans[tuple(selected['cell'])]
    output.mkdir(parents=True,exist_ok=False)
    (output/'region-search.json').write_text(json.dumps({'profile':'CodeWalker dictionary selection; GTA runtime unverified','probe_failures':evidence['failures'],'maps_examined':len(maps),'placements_found':len(placed),'candidates':summaries,'selected':selected},indent=2))
    tasks=[{'path':p,'export':export_name(p),'reasons':[]} for p in sorted(paths)]
    for task in tasks:
        if task['path'].endswith(('.ydr','.ydd','.yft')):
            for item in items:
                _,a=archetype(item['name']); asset=a.findtext('assetName',a.findtext('name')); key=a.findtext('drawableDictionary') if task['path'].endswith('.ydd') else asset
                if not key or key=='hash_00000000': key=asset
                if evidence[task['path'].split('.')[-1]].get(str(name_hash(key)),'').lower().replace('\\','/')==task['path']:task['reasons'].append('visual '+a.findtext('name'))
    (output/'tasks.json').write_text(json.dumps({'schema':1,'tasks':tasks,'texture_policy':{'scoped_textures':True,'asset_txds':txds,'txd_parents':parents}},indent=2))
    (output/'regions.json').write_text(json.dumps([{'bbox':selected['bbox']}]))
    (output/'placements.json').write_text(json.dumps([{'map':export_name(p['map']),'index':p['index'],'name':p['name'],'position':p['position']} for p in items],indent=2))
    print(json.dumps({'placements_found':len(placed),'candidates':len(summaries),'selected':selected},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('output',type=Path);p.add_argument('--bbox',nargs=4,type=float);p.add_argument('--evidence',default='codewalker-selection-01.json');a=p.parse_args();plan(a.root,a.output,a.evidence,a.bbox)
