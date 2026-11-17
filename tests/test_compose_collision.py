"""Focused conservative collision equivalence checks."""
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from compose import collision_geometry, collision_equivalent, collision_group, COLLISION_VERTEX_TOLERANCE_M


class CollisionEquivalenceTests(unittest.TestCase):
    def test_requires_topology_material_and_tolerance(self):
        def mesh(position='0 0 0 1 0 0 0 1 0',indices='0 1 2',material='road'):
            xml=f'<COLLADA><source id="mesh-positions"><float_array>{position}</float_array></source><triangles material="{material}" count="1"><p>{indices}</p></triangles></COLLADA>'
            return collision_geometry(ET.fromstring(xml))
        original=mesh()
        self.assertTrue(collision_equivalent(original,mesh('0.00001 0 0 1 0 0 0 1 0')))
        self.assertFalse(collision_equivalent(original,mesh('0.00003 0 0 1 0 0 0 1 0')))
        self.assertFalse(collision_equivalent(original,mesh(indices='0 2 1')))
        self.assertFalse(collision_equivalent(original,mesh(material='dirt')))
        self.assertEqual(COLLISION_VERTEX_TOLERANCE_M,2e-5)

    def test_requires_matching_source_and_collision_properties(self):
        obj={'collisionType':'Collision Mesh','decalType':'Collision Mesh','sourceArchetype':'collision_archive_path_a'}
        self.assertNotEqual(collision_group(obj,Path('same.dae')),
                            collision_group({**obj,'sourceArchetype':'collision_archive_path_b'},Path('same.dae')))
        self.assertNotEqual(collision_group(obj,Path('same.dae')),
                            collision_group({**obj,'isRenderEnabled':False},Path('same.dae')))


if __name__=='__main__': unittest.main()
