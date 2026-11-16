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
            self.assertEqual(stats,{'hits':1,'misses':0,'recovered':0})
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

    def test_collision_texture_equivalence_and_recovery(self):
        import collections
        import struct
        import numpy as np
        from resource_cache import cached_collision, cached_texture
        from convert import bounds_mesh, normalized_dds
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); cache=ResourceCache(root/'cache',recover=True)
            xml=root/'collision.xml'
            xml.write_text('<BoundsFile><Bounds type="Geometry"><GeometryCenter x="0" y="0" z="0"/><Vertices>0,0,0\n4,0,0\n0,4,0</Vertices><Polygons><Triangle v1="0" v2="1" v3="2"/></Polygons></Bounds></BoundsFile>')
            for origin in (np.zeros(3),np.array([2,3,0])):
                report={'unsupported_collision':collections.Counter(),'degenerate_triangles_removed':0}
                actual=cached_collision(cache,xml,origin,report,bounds_mesh)
                expected=bounds_mesh(xml,origin,{'unsupported_collision':collections.Counter(),'degenerate_triangles_removed':0})
                np.testing.assert_array_equal(actual[0]['v'],expected[0]['v'])
                np.testing.assert_array_equal(actual[0]['i'],expected[0]['i'])
            header=bytearray(128); header[:4]=b'DDS '
            struct.pack_into('<II',header,12,1,1); struct.pack_into('<I',header,80,2); struct.pack_into('<I',header,88,8)
            texture=root/'texture.dds'; texture.write_bytes(header+b'\xff')
            cached_texture(cache,texture,root/'a.dds',normalized_dds)
            cached_texture(cache,texture,root/'b.dds',lambda _:self.fail('Cache hit must skip normalization'))
            self.assertEqual((root/'a.dds').read_bytes(),(root/'b.dds').read_bytes())
            blob=next((cache.root/'blobs').glob('*.bin')); blob.write_bytes(b'corrupt')
            cached_texture(cache,texture,root/'c.dds',normalized_dds)
            self.assertEqual((root/'a.dds').read_bytes(),(root/'c.dds').read_bytes())
            self.assertGreater(cache.recovered,0)
            key='b'*64; cache.put(key,{'value':1}); cache.path(key).write_text('broken')
            self.assertIsNone(cache.get(key)); cache.put(key,{'value':2})
            self.assertEqual(cache.get(key),{'value':2})
            self.assertTrue(list((cache.root/'quarantine').iterdir()))

    def test_full_collision_texture_packages_match(self):
        import struct
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); source=root/'source'; fixture(source)
            (source/'road.ybn.xml').write_text('<BoundsFile><Bounds type="Geometry"><BoxMin x="0" y="0" z="0"/><BoxMax x="20" y="20" z="0"/><GeometryCenter x="0" y="0" z="0"/><Vertices>0,0,0\n20,0,0\n0,20,0</Vertices><Polygons><Triangle v1="0" v2="1" v3="2"/></Polygons></Bounds></BoundsFile>')
            header=bytearray(128); header[:4]=b'DDS '
            struct.pack_into('<II',header,12,1,1); struct.pack_into('<I',header,80,2); struct.pack_into('<I',header,88,8)
            (source/'missing_paint.dds').write_bytes(header+b'\xff')
            run(source,root/'shared',[0,0],10,maps=False,shared_cache=True)
            cached=run(source,root/'shared',[1,0],10,maps=False,shared_cache=True)
            plain=run(source,root/'plain',[1,0],10,maps=False)
            self.assertEqual((cached/'region.zip').read_bytes(),(plain/'region.zip').read_bytes())
            self.assertEqual((cached/'build/conversion_report.json').read_bytes(),(plain/'build/conversion_report.json').read_bytes())
            self.assertEqual(json.loads((cached/'region-manifest.json').read_text())['shared_cache']['hits'],3)
