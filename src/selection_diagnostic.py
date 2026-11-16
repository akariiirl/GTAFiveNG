"""Query actual CodeWalker dictionary evidence; never infer archive priority."""
import argparse,json
from pathlib import Path
from selected_region import name_hash,norm

def diagnose(evidence, name, candidates):
    extension=Path(name).suffix.lower().lstrip('.')
    if extension not in ('ymap','ytyp','ybn','ydr','ydd','yft','ytd'):
        raise ValueError('Unsupported resource kind')
    key=str(name_hash(Path(name).stem))
    winner=evidence[extension].get(key)
    candidates=sorted(set(norm(p) for p in candidates))
    selected=norm(winner) if winner else None
    if selected and selected not in candidates:
        status='evidence_catalog_mismatch'
    else:
        status='selected' if selected else 'absent_from_dictionary'
    return {'name':name,'hash':key,'status':status,'selected':selected,
            'candidates':candidates,'profile':'CodeWalker dictionary selection; GTA runtime unverified',
            'probe_failures':evidence.get('failures',[])}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('evidence',type=Path);p.add_argument('inventory',type=Path);p.add_argument('name');a=p.parse_args()
    candidates=[]
    with a.inventory.open() as f:
        for line in f:
            r=json.loads(line)
            if r['name'].lower()==a.name.lower():candidates.append(r['path'])
    print(json.dumps(diagnose(json.loads(a.evidence.read_text()),a.name,candidates),indent=2))
