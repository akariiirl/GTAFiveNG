import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from resource_cache import ResourceCache
from test_region import fixture
from region import run


class ResourceCacheTests(unittest.TestCase):
    def test_neighboring_regions_reuse_and_match_uncached_package(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            root=Path(d); source=root/'source'; fixture(source)
            first=run(source,root/'work',[0,0],10,maps=False,shared_cache=True)
            second=run(source,root/'work',[1,0],10,maps=False,shared_cache=True)
            stats=json.loads((second/'region-manifest.json').read_text())['shared_cache']
            self.assertEqual(stats,{'hits':1,'misses':0})
            plain=run(source,root/'plain',[1,0],10,maps=False)
            self.assertEqual((second/'region.zip').read_bytes(),(plain/'region.zip').read_bytes())
            self.assertEqual((second/'build/conversion_report.json').read_bytes(),(plain/'build/conversion_report.json').read_bytes())
            path=source/'toy.ydr.xml'; path.write_text(path.read_text().replace('4 0 0','5 0 0'))
            changed=run(source,root/'work',[2,0],10,maps=False,shared_cache=True)
            self.assertEqual(json.loads((changed/'region-manifest.json').read_text())['shared_cache']['misses'],1)

    def test_verified_immutable_entries(self):
        with tempfile.TemporaryDirectory() as d:
            cache=ResourceCache(Path(d)); key='a'*64
            cache.put(key,{'original':[1,2]}); self.assertEqual(cache.get(key),{'original':[1,2]})
            cache.put(key,{'original':[1,2]})
            with self.assertRaises(ValueError): cache.put(key,{'changed':True})
            path=cache.path(key); data=json.loads(path.read_text()); data['payload']='{}'; path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'Corrupt'): cache.get(key)
            with self.assertRaises(ValueError): cache.get('../escape')

    def test_replay_preserves_texture_material_and_report_effects(self):
        import numpy as np
        from resource_cache import cached_drawable
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); source=root/'drawable.xml'; source.write_text('synthetic test input')
            cache=ResourceCache(root/'cache'); calls=[]
            def convert(xml,name,materials,textures,report):
                calls.append(name); materials['mat']={'name':'mat','Stages':[{'diffuseMap':'paint.dds'}]}
                textures['paint']['used']=True
                report['missing_textures'].add('missing')
                report['skipped_skinned_models']={'skin'}
                report['degenerate_triangles_removed']=2
                return [{'v':np.array([[0.,0,0],[1,0,0],[0,1,0]]),'i':np.array([[0,1,2]]),'material':'mat','n':None}]
            snapshots=[]
            for _ in range(2):
                materials={}; textures={'paint':{'path':root/'paint.dds','used':False}}
                report={'missing_textures':set(),'degenerate_triangles_removed':0}
                meshes=cached_drawable(cache,source,'toy',materials,textures,report,convert)
                snapshots.append((materials,textures['paint']['used'],report))
                self.assertEqual(meshes[0]['i'].tolist(),[[0,1,2]])
            self.assertEqual(calls,['toy'])
            self.assertEqual(snapshots[0],snapshots[1])
            self.assertTrue(snapshots[1][1])
