"""Synthetic fixtures only; no game data."""
import hashlib,json,sys,tempfile,types,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from selection_diagnostic import diagnose
from selected_region import name_hash
from compare_collision import height_hits,triangle_keys
from extraction import execute,export_name
from convert import drawable
from test_region import fixture

class EvidenceTests(unittest.TestCase):
    def test_dictionary_selection_is_not_candidate_order(self):
        evidence={'ybn':{str(name_hash('road')):'UPDATE.RPF\\nested.rpf\\road.ybn'}}
        candidates=['z.rpf/road.ybn','update.rpf/nested.rpf/road.ybn']
        result=diagnose(evidence,'road.ybn',candidates)
        self.assertEqual(result['selected'],candidates[1])
        self.assertEqual(result,diagnose(evidence,'road.ybn',list(reversed(candidates))))
        self.assertEqual(diagnose(evidence,'road.ybn',[candidates[0]])['status'],'evidence_catalog_mismatch')
        self.assertEqual(diagnose({'ybn':{}},'road.ybn',candidates)['status'],'absent_from_dictionary')
        self.assertEqual(name_hash('hash_1234ABCD'),0x1234ABCD)

    def test_height_queries_keep_stacked_surfaces(self):
        t=np.array([[[0,0,2],[2,0,2],[0,2,2]],[[0,0,5],[2,0,5],[0,2,5]]],dtype=float)
        np.testing.assert_allclose(height_hits(t,[.5,.5]),[2,5])
        self.assertEqual(len(height_hits(t,[3,3])),0)
        self.assertEqual(triangle_keys(t),triangle_keys(t[:,::-1]))

    def test_repeated_placements_do_not_cycle_embedded_parent(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); path='base.rpf/toy.ydr'; exported=export_name(path)
            files={exported:b'<Drawable/>','textures/paint.dds':b'synthetic'}
            (root/'textures').mkdir()
            for n,b in files.items():(root/n).write_bytes(b)
            (root/(exported[:-4]+'.receipt.json')).write_text(json.dumps({'Fingerprint':'synthetic','Files':{n:hashlib.sha256(b).hexdigest().upper() for n,b in files.items()}}))
            plan={'tasks':[{'path':path,'export':exported,'reasons':['visual toy','visual toy']}], 'texture_policy':{'asset_txds':{'toy':'parent'}}}
            execute(plan,'r','g',root,root/'plan.json',runner=lambda *a,**k:types.SimpleNamespace(returncode=0))
            policy=json.loads((root/'dependency-policy.json').read_text())
            embedded=policy['asset_txds']['toy']
            self.assertEqual(policy['txd_parents'][embedded],'parent')
            self.assertEqual(plan['texture_policy']['asset_txds']['toy'],'parent')

    def test_blank_vertex_rows_and_empty_buffer(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'source';fixture(source);p=source/'toy.ydr.xml'
            original=p.read_text();p.write_text(original.replace('\n','\n\n'))
            def read():return drawable(p,'toy',{}, {},{'degenerate_triangles_removed':0,'missing_textures':set()})
            self.assertEqual(len(read()[0]['i']),1)
            import re
            p.write_text(re.sub(r'(<VertexBuffer>.*?<Data>).*?(</Data>)',r'\1\n\2',original,flags=re.S))
            with self.assertRaisesRegex(ValueError,'Empty vertex buffer'):read()
