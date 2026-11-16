"""Validate generated dependencies and write a deterministic, versioned local ZIP."""
from pathlib import Path
import argparse, hashlib, json, zipfile
import xml.etree.ElementTree as ET

def validate(root):
    level=root/'levels/los_santos_fazes'; objects=[]; materials={}; errors=[]
    for p in level.rglob('items.level.json'):
        objects.extend(json.loads(l) for l in p.read_text().splitlines() if l.strip())
    names=[o['name'] for o in objects]
    if len(names)!=len(set(names)): errors.append('Duplicate scene names')
    for o in objects:
        if '__parent' in o and o['__parent'] not in names: errors.append('Missing parent '+o['__parent'])
        if 'shapeName' in o and not (root/o['shapeName'].lstrip('/')).exists(): errors.append('Missing shape '+o['shapeName'])
    for p in level.rglob('*.materials.json'):
        materials.update(json.loads(p.read_text()))
    for name,mat in materials.items():
        for stage in mat.get('Stages',[]):
            for key,val in stage.items():
                if key.endswith('Map') and isinstance(val,str) and val.startswith('/levels/') and not (root/val.lstrip('/')).exists(): errors.append('Missing texture '+val)
    ns={'c':'http://www.collada.org/2005/11/COLLADASchema'}
    for p in level.rglob('*.dae'):
        tree=ET.parse(p)
        for tri in tree.findall('.//c:triangles',ns):
            if tri.get('material') not in materials: errors.append('Missing material '+tri.get('material'))
            if len(tri.findtext('c:p',namespaces=ns).split())!=int(tri.get('count'))*3: errors.append('Bad triangles '+p.name)
    if errors: raise ValueError('\n'.join(errors))
    return {'scene_objects':len(objects),'shapes':len(list(level.rglob('*.dae'))),'materials':len(materials),'dependency_errors':errors,'note':'Structural validation only; does not prove visual fidelity or physics coverage.'}

def package(root,target):
    report=validate(root); target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists(): raise FileExistsError('Preserving existing build: '+str(target))
    files=sorted((root/'levels').rglob('*'))
    manifest=[]
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:
            if not p.is_file(): continue
            name=p.relative_to(root).as_posix(); data=p.read_bytes()
            info=zipfile.ZipInfo(name,date_time=(2026,11,15,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,data); manifest.append({'path':name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        assert all(n.startswith('levels/los_santos_fazes/') for n in z.namelist())
    report.update(files=len(manifest),zip_bytes=target.stat().st_size,zip_sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    target.with_suffix('.manifest.json').write_text(json.dumps({'validation':report,'files':manifest},indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('root',type=Path); p.add_argument('target',type=Path)
    a=p.parse_args(); package(a.root,a.target)
