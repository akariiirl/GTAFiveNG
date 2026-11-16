import collections
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from convert import bounds_mesh, quat_matrix, valid_mesh
from primitives import rounded_shape
from region import run
from test_region import fixture
from validate_surfaces import validate


class CollisionTests(unittest.TestCase):
    def test_mirrored_collision_transform(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'synthetic.xml'
            path.write_text('''<BoundsFile><Bounds type="Geometry"><CompositeTransform>-1 0 0 0 0 1 0 0 0 0 1 0 10 0 0 1</CompositeTransform><GeometryCenter x="0" y="0" z="0"/><Vertices>0,0,0
4,0,0
0,4,0</Vertices><Polygons><Triangle v1="0" v2="1" v3="2"/></Polygons></Bounds></BoundsFile>''')
            report = {'unsupported_collision':collections.Counter(), 'degenerate_triangles_removed':0}
            mesh = bounds_mesh(path, np.array([2,0,0]), report)[0]
            np.testing.assert_allclose(mesh['v'], [[8,0,0],[4,0,0],[8,4,0]])
            triangle = mesh['v'][mesh['i'][0]]
            self.assertGreater(np.cross(triangle[1]-triangle[0], triangle[2]-triangle[0])[2], 0)

    def test_no_collision_is_missing_evidence(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            root = Path(d); source = root/'source'; fixture(source)
            text = (source/'toy.ymap.xml').read_text().replace('>toy<', '>sc1_rd_r_synthetic<')
            (source/'toy.ymap.xml').write_text(text)
            (source/'toy.ydr.xml').rename(source/'sc1_rd_r_synthetic.ydr.xml')
            target = run(source, root/'work', [0,0], 10, maps=False)
            result = validate(target/'build', step=1)
            self.assertFalse(result['collision_evidence_available'])
            self.assertEqual(result['sample_count'], 2)
            self.assertEqual(len(result['failures']), 2)
            self.assertIsNone(result['failures'][0]['height_error'])
            with self.assertRaises(ValueError): validate(target/'build', step=0)
            (source/'road.ybn.xml').write_text('<BoundsFile><Bounds type="Geometry"><BoxMin x="0" y="0" z="0"/><BoxMax x="20" y="20" z="0"/><GeometryCenter x="0" y="0" z="0"/><Vertices>0,0,0\n20,0,0\n0,20,0</Vertices><Polygons><Triangle v1="0" v2="1" v3="2"/></Polygons></Bounds></BoundsFile>')
            aligned = run(source, root/'work', [0,0], 10, maps=False)
            self.assertEqual(validate(aligned/'build', step=1)['within_half_meter'], 2)


    def test_primitive_variants_and_invalid_transforms(self):
        for kind in ('Sphere','Capsule','Cylinder'):
            end = [0,0,0] if kind == 'Sphere' else [3,2,4]
            vertices, faces = rounded_shape([0,0,0], end, 1, kind)
            self.assertGreater(len(faces), 0)
            self.assertEqual(valid_mesh(vertices, faces)[1], 0)
        with self.assertRaises(ValueError): rounded_shape([0,0,0],[0,0,1],1,'Cube')
        with self.assertRaises(ValueError): rounded_shape([0,0,0],[0,0,1],1,'Sphere',sides=2)
        with self.assertRaises(ValueError): quat_matrix(ET.fromstring('<Item><rotation x="nan" y="0" z="0" w="1"/></Item>'))
