"""Compare candidate paths with CodeWalker mount evidence, without choosing GTA precedence."""
import argparse
import json
from pathlib import Path


def normalize(path):
    value=path.replace('\\','/').lower().strip('/')
    if not value or any(part in ('','.','..') for part in value.split('/')) or ':' in value:
        raise ValueError('Invalid physical archive path')
    return value


def patched_path(path, patches):
    """Resolve exact file or nested-archive replacement, preserving resource suffix."""
    current=normalize(path); seen=set(); used=set()
    while True:
        if current in seen: raise ValueError('CodeWalker patch mapping cycle')
        seen.add(current)
        matches=[key for key in patches if current==key or current.startswith(key+'/')]
        if not matches: return current
        key=max(matches,key=len)
        if key in used: raise ValueError('CodeWalker patch mapping cycle')
        used.add(key)
        current=patches[key]+current[len(key):]


def classify(conflicts, evidence):
    if evidence.get('failures'): raise ValueError('Mount evidence has errors')
    active={normalize(path) for path in evidence['active'].values()}
    patches={}
    for key,value in evidence['patches'].items():
        key=normalize(key); value=normalize(value)
        if key in patches and patches[key]!=value: raise ValueError('Conflicting normalized patch mappings')
        patches[key]=value
    result=[]
    for group in conflicts:
        candidates={normalize(p) for p in group['candidates']}; matches=set(); substitutions={}
        for candidate in sorted(candidates):
            effective=patched_path(candidate,patches); substitutions[candidate]=effective
            if effective in candidates and effective.rsplit('/',1)[0] in active: matches.add(effective)
        result.append({'name':group['name'],'candidates':sorted(candidates),'patch_substitutions':substitutions,
                       'active_candidates':sorted(matches),'status':{0:'none',1:'one'}.get(len(matches),'multiple')})
    return {'caveat':'CodeWalker approximation; active archive membership does not prove GTA runtime precedence.',
            'conflicts':result}


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--conflicts',type=Path,required=True); p.add_argument('--mounts',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    conflicts=json.loads(a.conflicts.read_text(encoding='utf-8'))['relevant']
    evidence=json.loads(a.mounts.read_text(encoding='utf-8'))
    with a.output.open('x',encoding='utf-8') as f: json.dump(classify(conflicts,evidence),f,indent=2)
