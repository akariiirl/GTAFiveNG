"""Verify exact extraction receipts and prepare a separate XML view for conversion."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import shutil
from types import SimpleNamespace
import xml.etree.ElementTree as ET
from dependencies import joaat
from extraction import execute
from local_workflow import safe_metadata


def prepare(root, workspace, target_name='prepared'):
    tasks=json.loads((workspace/'tasks.json').read_text()); source=workspace/'extracted'
    execute(tasks,'unused','unused',source,workspace/'tasks.json',runner=lambda *a,**k:SimpleNamespace(returncode=0))
    names=defaultdict(set)
    snapshot=Path(json.loads((root/'catalog/bootstrap.json').read_text())['snapshot'])
    with (snapshot/'inventory.jsonl').open() as stream:
        for line in stream:
            r=json.loads(line); n=Path(r['name']).stem
            try:names[joaat(n)].add(n)
            except UnicodeEncodeError:pass
    for p in source.glob('*.ytyp.xml'):
        for i in ET.fromstring(safe_metadata(p.read_bytes())).findall('.//archetypes/Item'):
            n=i.findtext('name','')
            if n and not n.startswith('hash_'):
                try:names[joaat(n)].add(n)
                except UnicodeEncodeError:pass
    replaced=0; unresolved=set()
    def replace(m):
        nonlocal replaced
        value=int(m.group(1),16); choices=names.get(value,set())
        if len(choices)==1:
            replaced+=1; return '>'+next(iter(choices))+'<'
        if value:unresolved.add(m.group(1))
        return m.group(0)
    target=workspace/target_name; target.mkdir(exist_ok=False)
    placements=workspace/'placements.json'; selected=defaultdict(set)
    if placements.exists():
        for p in json.loads(placements.read_text()):selected[p['map']].add(p['index'])
    for p in source.iterdir():
        if p.is_dir(): shutil.copytree(p,target/p.name)
        elif p.name.endswith('.xml'):
            data=safe_metadata(p.read_bytes()).decode('utf-8-sig')
            if placements.exists() and p.name.endswith('.ymap.xml'):
                tree=ET.fromstring(data); entities=tree.find('entities')
                if entities is not None:
                    for index,item in enumerate(list(entities)):
                        if index not in selected[p.name]:entities.remove(item)
                data=ET.tostring(tree,encoding='unicode')
            (target/p.name).write_bytes(re.sub(r'>hash_([0-9a-fA-F]{8})<',replace,data).encode('utf-8'))
    shutil.copyfile(source/'dependency-policy.json',target/'dependency-policy.json')
    result={'verified_receipts':len(tasks['tasks']),'hash_replacements':replaced,'remaining_hash_references':sorted(unresolved),'original_exports_preserved':True}
    (target/'preparation.json').write_text(json.dumps(result,indent=2));print(json.dumps({**result,'remaining_hash_references':len(unresolved)},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('workspace',type=Path);p.add_argument('--target',default='prepared');a=p.parse_args();prepare(a.root,a.workspace,a.target)
