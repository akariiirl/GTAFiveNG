import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from test_region import fixture
from extraction import build_tasks,execute,export_name,normalize


class ExtractionTests(unittest.TestCase):
    def test_dependency_closure_and_precedence(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); source=root/'source'; fixture(source)
            (source/'types.ytyp.xml').write_text('<CMapTypes><archetypes><Item><name>toy</name><assetName>pack</assetName><assetType>ASSET_TYPE_DRAWABLEDICTIONARY</assetType><textureDictionary>child</textureDictionary></Item></archetypes></CMapTypes>')
            inventory=[{'path':p} for p in ['base.rpf/toy.ymap','base.rpf/types.ytyp','base.rpf/pack.ydd','update.rpf/pack.ydd','base.rpf/child.ytd','base.rpf/parent.ytd','base.rpf/unknown.ybn']]
            inventory.append({'path':'base.rpf/road.ybn','bounds_xy':[-1,-1,10,10]})
            (source/'dependency-policy.json').write_text(json.dumps({'txd_parents':{'child':'parent'},'archive_priorities':{'update.rpf':10}}))
            plan=build_tasks(source,inventory,center=[0,0],radius=10)
            paths={task['path'] for task in plan['tasks']}
            self.assertIn('update.rpf/pack.ydd',paths); self.assertNotIn('base.rpf/pack.ydd',paths)
            self.assertIn('base.rpf/parent.ytd',paths); self.assertIn('base.rpf/road.ybn',paths)
            self.assertNotIn('base.rpf/unknown.ybn',paths)
            self.assertTrue(any(x['status']=='collision bounds unknown' for x in plan['diagnostics']))
            self.assertEqual(plan,build_tasks(source,inventory,center=[0,0],radius=10))
            (source/'dependency-policy.json').write_text('{}')
            self.assertTrue(any(x['status']=='ambiguous' for x in build_tasks(source,inventory,center=[0,0],radius=10)['diagnostics']))

    def test_protocol_and_preservation(self):
        for path in ('../x.ydr','/x.ydr','C:/x.ydr','a//x.ydr','a/x.exe'):
            with self.assertRaises(ValueError): normalize(path)
        self.assertEqual(export_name('BASE.RPF\\toy.ydr'),export_name('base.rpf/toy.ydr'))
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); calls=[]; plan={'schema':1,'tasks':[{'path':'base.rpf/toy.ydr','export':export_name('base.rpf/toy.ydr')}]}
            def runner(command,check):
                import hashlib
                calls.append(command); out=root/'out'; out.mkdir(exist_ok=True)
                name=plan['tasks'][0]['export']; (out/name).write_text('<Drawable/>')
                (out/(name[:-4]+'.receipt.json')).write_text(json.dumps({'Fingerprint':'synthetic','Files':{name:hashlib.sha256((out/name).read_bytes()).hexdigest().upper()}}))
                return types.SimpleNamespace(returncode=0)
            execute(plan,'reader.dll','local-game',root/'out',root/'plan.json',runner)
            self.assertEqual(calls[0][-2:],[ '--tasks', str(root/'plan.json')])
            with self.assertRaises(FileExistsError): execute({'schema':1,'tasks':[]},'r','g',root/'out',root/'plan.json',runner)
            def failure(command,check): return types.SimpleNamespace(returncode=1)
            with self.assertRaises(RuntimeError): execute(plan,'r','g',root/'out',root/'plan.json',failure)
