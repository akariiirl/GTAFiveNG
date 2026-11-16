import contextlib
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from local_workflow import run_workflow,plan_execution,active_metadata
from extraction import export_name
from test_region import fixture


class LocalWorkflowTests(unittest.TestCase):
    def test_full_synthetic_inventory_to_isolated_package_and_resume(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            root=Path(d); source=root/'fixtures'; fixture(source)
            (source/'types.ytyp.xml').write_text('<CMapTypes><archetypes><Item><name>toy</name><assetName>toy</assetName><assetType>ASSET_TYPE_DRAWABLE</assetType></Item></archetypes></CMapTypes>')
            game=root/'synthetic-game'; game.mkdir(); (game/'GTA5.exe').write_text('original synthetic placeholder')
            reader=root/'reader.dll'; reader.write_text('original synthetic placeholder')
            calls=[]; failed=[False]; partial=[]; reused=[]
            def runner(command,check):
                calls.append(command)
                output=Path(command[3]); output.mkdir(parents=True,exist_ok=True)
                if command[-1]=='--bootstrap':
                    snapshot=output/'snapshots/synthetic-v1'; snapshot.mkdir(parents=True,exist_ok=True); inventory=[]
                    for path in source.glob('*.xml'):
                        name=path.name[:-4]; resource='base.rpf/'+name; record={'path':resource,'name':name,'size':path.stat().st_size}
                        if name.endswith(('.ymap','.ytyp')):
                            record.update(xml=export_name(resource),xml_sha256=hashlib.sha256(path.read_bytes()).hexdigest()); shutil.copyfile(path,snapshot/record['xml'])
                        inventory.append(record)
                    (snapshot/'inventory.jsonl').write_text('\n'.join(json.dumps(r) for r in inventory))
                    (output/'bootstrap.json').write_text(json.dumps({'snapshot':str(snapshot),'errors':0}))
                else:
                    plan=json.loads(Path(command[-1]).read_text())
                    if failed[0]: reused.append((output/plan['tasks'][0]['export']).exists())
                    for task in plan['tasks']:
                        filename=task['export']; data=(source/(task['path'].rsplit('/',1)[-1]+'.xml')).read_bytes()
                        (output/filename).write_bytes(data)
                        (output/(filename[:-4]+'.receipt.json')).write_text(json.dumps({'Fingerprint':'synthetic','Files':{filename:hashlib.sha256(data).hexdigest().upper()}}))
                        if not failed[0]:
                            failed[0]=True; marker=output/'partial-marker.tmp'; marker.write_text('interrupted evidence'); partial.append(marker)
                            return types.SimpleNamespace(returncode=1)
                return types.SimpleNamespace(returncode=0)
            regions=[{'center':[0,0],'radius':10},{'center':[1,0],'radius':10}]
            with self.assertRaises(RuntimeError): run_workflow(regions,root/'work',game,reader,allow_missing=True,native_runner=runner)
            handoff=run_workflow(regions,root/'work',game,reader,allow_missing=True,native_runner=runner)
            result=json.loads(handoff.read_text()); self.assertFalse(result['in_game_verified'])
            self.assertTrue(Path(result['profile_package']).is_file())
            previous=Path(result['package']).stat().st_mtime_ns
            self.assertEqual(run_workflow(regions,root/'work',game,reader,allow_missing=True,native_runner=runner),handoff)
            self.assertEqual(Path(result['package']).stat().st_mtime_ns,previous)
            self.assertEqual(len([c for c in calls if '--tasks' in c]),2)
            self.assertTrue(all(reused)); self.assertEqual(partial[0].read_text(),'interrupted evidence')
            self.assertEqual((game/'GTA5.exe').read_text(),'original synthetic placeholder')

    def test_dry_run_touches_no_game_or_workspace(self):
        with tempfile.TemporaryDirectory() as d:
            workspace=Path(d)/'absent'
            result=plan_execution([{'bbox':[0,0,10,10]}],workspace,'unavailable-game')
            self.assertEqual(len(result['stages']),9); self.assertFalse(result['game_files_accessed']); self.assertFalse(workspace.exists())

    @unittest.skipUnless(shutil.which('pwsh'),'PowerShell available on Windows CI')
    def test_powershell_dry_run(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); regions=root/'regions.json'; regions.write_text('[{"center":[0,0],"radius":10}]')
            command=['pwsh','-NoProfile','-File',str(Path(__file__).resolve().parents[1]/'tools/run_local.ps1'),'-Regions',str(regions),'-Workspace',str(root/'absent'),'-DryRun']
            result=subprocess.run(command,check=True,capture_output=True,text=True)
            self.assertFalse(json.loads(result.stdout)['game_files_accessed']); self.assertFalse((root/'absent').exists())

    def test_active_metadata_requires_precedence_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); snapshot=root/'snapshot'; snapshot.mkdir(); records=[]
            for archive,body in [('base.rpf','base'),('update.rpf','updated')]:
                resource=archive+'/toy.ymap'; filename=export_name(resource); (snapshot/filename).write_text(body)
                records.append({'path':resource,'name':'toy.ymap','xml':filename,'xml_sha256':hashlib.sha256(body.encode()).hexdigest()})
            (snapshot/'inventory.jsonl').write_text('\n'.join(json.dumps(r) for r in records))
            with self.assertRaisesRegex(ValueError,'Ambiguous'): active_metadata(snapshot,{},root/'ambiguous')
            active_metadata(snapshot,{'archive_priorities':{'update.rpf':10}},root/'selected')
            self.assertEqual(len(list((root/'selected').glob('*.ymap.xml'))),1)
            self.assertEqual(next((root/'selected').glob('*.ymap.xml')).read_text(),'updated')
