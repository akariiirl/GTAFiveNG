import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from lod import simplify,validate_settings
from convert import valid_mesh
from test_region import fixture
from region import run


class LODTests(unittest.TestCase):
    def test_grid_reduction_determinism_and_boundary(self):
        vertices=np.array([[x,y,0.] for x in range(8) for y in range(8)])
        faces=[]
        for x in range(7):
            for y in range(7):
                a=x*8+y; faces.extend([[a,a+8,a+1],[a+8,a+9,a+1]])
        mesh={'v':vertices,'i':np.array(faces),'material':'synthetic','uv':vertices[:,:2]/7}
        output,report=simplify(mesh,2)
        self.assertLess(len(output['i']),len(faces)); self.assertEqual(valid_mesh(output['v'],output['i'])[1],0)
        second,again=simplify(mesh,2); np.testing.assert_array_equal(output['v'],second['v']); self.assertEqual(report,again)
        boundary=vertices[(vertices[:,0]==0)|(vertices[:,0]==7)|(vertices[:,1]==0)|(vertices[:,1]==7)]
        for vertex in boundary: self.assertTrue(np.any(np.all(output['v']==vertex,axis=1)))
        np.testing.assert_array_equal(mesh['v'],vertices)
        with self.assertRaises(ValueError): simplify(mesh,0)
        with self.assertRaises(ValueError): validate_settings([2,1],None)

    def test_preview_excluded_from_package_and_budget_failure(self):
        import zipfile
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            root=Path(d); source=root/'source'; fixture(source)
            plain=run(source,root/'plain',[0,0],10,maps=False)
            preview=run(source,root/'preview',[0,0],10,maps=False,lod_sizes=[2])
            self.assertTrue(list((preview/'build/lod_previews').glob('*/*.dae')))
            self.assertEqual((plain/'region.zip').read_bytes(),(preview/'region.zip').read_bytes())
            (source/'road.ybn.xml').write_text('<BoundsFile><Bounds type="Geometry"><BoxMin x="0" y="0" z="0"/><BoxMax x="20" y="20" z="0"/><GeometryCenter x="0" y="0" z="0"/><Vertices>0,0,0\n20,0,0\n0,20,0</Vertices><Polygons><Triangle v1="0" v2="1" v3="2"/></Polygons></Bounds></BoundsFile>')
            with self.assertRaisesRegex(ValueError,'budget exceeded'): run(source,root/'budget',[0,0],10,maps=False,max_collision_triangles=0)
            diagnostics=list((root/'budget').rglob('collision_budget.json')); self.assertEqual(len(diagnostics),1)
            self.assertEqual(json.loads(diagnostics[0].read_text())['observed_triangles'],1)
            self.assertFalse(list((root/'budget').rglob('region.zip')))
