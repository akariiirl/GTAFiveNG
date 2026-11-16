"""Synthetic native task-protocol smoke check; never loads keys or game archives."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from extraction import export_name

with tempfile.TemporaryDirectory() as directory:
    plan=Path(directory)/'plan.json'
    paths=['base.rpf/synthetic.'+ext for ext in ('ymap','ytyp','ydr','ydd','yft','ytd','ybn')]
    plan.write_text(json.dumps({'schema':1,'tasks':[{'path':p} for p in paths]}))
    command=['dotnet',sys.argv[1],'--validate-plan',str(plan)]
    actual=json.loads(subprocess.run(command,check=True,capture_output=True,text=True).stdout)
    assert actual==[{'path':p,'export':export_name(p)} for p in sorted(paths)]
    plan.write_text(json.dumps({'schema':1,'tasks':[{'path':'../escape.ydr'}]}))
    assert subprocess.run(command,capture_output=True).returncode!=0
print('Native/Python synthetic task protocol agrees; unsafe paths rejected.')

with tempfile.TemporaryDirectory() as directory:
    root=Path(directory); fixture=root/'fixture.json'; output=root/'index'
    child='<Item type="Box"><BoxMin x="-1" y="-2" z="0"/><BoxMax x="1" y="2" z="1"/><CompositeTransform>1 0 0 0 0 1 0 0 0 0 1 0 10 20 0 1</CompositeTransform></Item>'
    bounds='<BoundsFile><Bounds type="Composite"><BoxMin x="9" y="18" z="0"/><BoxMax x="11" y="22" z="1"/><Children>'+child+'</Children></Bounds></BoundsFile>'
    items=[{'path':'base.rpf/nested.rpf/toy.ymap','xml':'<CMapData><archetypeName>hash_deadbeef</archetypeName></CMapData>'},
           {'path':'base.rpf/nested.rpf/road.ybn','bounds_xml':bounds}, {'path':'base.rpf/missing.ybn'}]
    fixture.write_text(json.dumps(items)); command=['dotnet',sys.argv[1],'--bootstrap-fixture',str(fixture),str(output)]
    process=subprocess.run(command,capture_output=True,text=True)
    assert process.returncode==0, process.stdout+process.stderr+''.join(p.read_text() for p in output.rglob('index-errors.jsonl'))
    first=json.loads(process.stdout)
    records=[json.loads(line) for line in (Path(first['snapshot'])/'inventory.jsonl').read_text().splitlines()]
    road=next(r for r in records if r['path'].endswith('road.ybn')); assert road['bounds_xy']==[9,18,11,22]
    assert any(r['hash_only_references']==['hash_deadbeef'] for r in records)
    items[0]['fail_decode']=True; fixture.write_text(json.dumps(items))
    assert json.loads(subprocess.run(command,check=True,capture_output=True,text=True).stdout)==first
    items[0]['fail_decode']=False; items[0]['xml']+='<changed/>'; fixture.write_text(json.dumps(items))
    changed=json.loads(subprocess.run(command,check=True,capture_output=True,text=True).stdout)
    assert changed['snapshot']!=first['snapshot'] and Path(first['snapshot']).exists()
    items[1]['bounds_xml']=bounds.replace('x="9"','x="99"'); fixture.write_text(json.dumps(items))
    assert subprocess.run(command,capture_output=True).returncode!=0
print('Native bootstrap: nested provenance, transformed bounds, hash diagnostics, resume, invalidation and invalid bounds passed.')
