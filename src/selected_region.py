"""Plan an explicitly CodeWalker-selected prototype from existing catalog evidence."""
import argparse
from collections import Counter,defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from dependencies import joaat
from extraction import export_name
from local_workflow import safe_metadata


def norm(path): return path.lower().replace('\\','/')
def name_hash(name):
    match=re.fullmatch(r'hash_([0-9a-fA-F]{8})',name)
    return int(match[1],16) if match else joaat(name)


def plan(root, output, evidence_file='codewalker-selection-01.json'):
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
        for item in read(path).findall('entities/Item'):
            if item.findtext('lodLevel') not in ('LODTYPES_DEPTH_HD','LODTYPES_DEPTH_ORPHANHD'): continue
            pos=item.find('position'); xyz=[float(pos.get(k)) for k in 'xyz']
            if -850<=xyz[0]<=450 and -2000<=xyz[1]<=-900:
                result.append({'map':path,'name':item.findtext('archetypeName'),'position':xyz})
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
    for cell,items in sorted(cells.items()):
        if not 15<=len(items)<=800: continue
        paths=set(); missing=[]; txds={}; road=0; embedded=[]; parents={}
        for p in items:
            paths.add(p['map']); typ,a=archetype(p['name'])
            if a is None: missing.append('archetype:'+p['name']); continue
            paths.add(typ); name=a.findtext('name'); asset=a.findtext('assetName',name); kind=a.findtext('assetType')
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
        box=[cell[0]*100,cell[1]*100,(cell[0]+1)*100,(cell[1]+1)*100]
        collision=[]
        for path in evidence['ybn'].values():
            path=norm(path); r=records.get(path); b=r.get('bounds_xy') if r else None
            if b and b[0]<=box[2] and b[2]>=box[0] and b[1]<=box[3] and b[3]>=box[1] and not r['name'].startswith('ma@'):
                collision.append(path)
        paths.update(collision)
        summary={'cell':list(cell),'bbox':box,'hd_placements':len(items),'road_placements':road,'resource_tasks':len(paths),'collision_resources':len(collision),'missing':sorted(set(missing)),'embedded_txd_verification_pending':sorted(set(embedded))}
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
    print(json.dumps({'placements_found':len(placed),'candidates':len(summaries),'selected':selected},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('output',type=Path);p.add_argument('--evidence',default='codewalker-selection-01.json');a=p.parse_args();plan(a.root,a.output,a.evidence)
