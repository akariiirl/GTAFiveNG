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
