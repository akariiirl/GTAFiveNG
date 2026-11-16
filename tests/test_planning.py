import json
from pathlib import Path
import tempfile
import unittest
from test_region import fixture
from planning import chunk_id, plan, reconcile
from dependencies import joaat, resolve_hash_reference


class PlanningTests(unittest.TestCase):
    def test_hash_only_archetype_resolves_from_unique_ytyp_name(self):
        self.assertEqual(joaat('adder'), 0xb779a091)
        with tempfile.TemporaryDirectory() as d:
            source = Path(d)/'source'; fixture(source)
            (source/'types.ytyp.xml').write_text('<CMapTypes><archetypes><Item><name>toy</name><assetName>toy</assetName></Item></archetypes></CMapTypes>')
            ymap = source/'toy.ymap.xml'
            ymap.write_text(ymap.read_text().replace('<archetypeName>toy</archetypeName>', f'<archetypeName>hash_{joaat("toy"):08x}</archetypeName>'))
            result = plan(source, center=[0, 0], radius=10)
            self.assertIn('toy', result['dependencies'])
            self.assertEqual(result['hash_reference_diagnostics'][0]['status'], 'resolved')
            self.assertEqual(resolve_hash_reference('hash_deadbeef', {0xdeadbeef: set()}),
                             ('hash_deadbeef', {'reference': 'hash_deadbeef', 'status': 'unresolved', 'candidates': []}))

    def test_bounds_dependencies_and_resume(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d)/'source'; fixture(source)
            result = plan(source, bbox=[0, -1, 10, 1], chunk_size=5)
            self.assertEqual(result['chunks'], {'0_0': ['absent', 'toy'], '2_0': ['toy']})
            self.assertEqual(result['plan_id'], plan(source, bbox=[0,-1,10,1], chunk_size=5)['plan_id'])
            self.assertEqual(result['dependencies']['toy']['export'], 'toy.ydr.xml')
            state = reconcile(result, source)
            self.assertEqual(state['tasks']['toy']['state'], 'verified')
            self.assertEqual(state['tasks']['absent']['state'], 'pending')
            (source/'toy.ydr.xml').write_text('changed')
            self.assertEqual(reconcile(result, source, state)['tasks']['toy']['state'], 'pending')
            self.assertNotEqual(result['plan_id'], plan(source, bbox=[0,-1,10,1])['plan_id'])

    def test_radius_and_bad_bounds(self):
        self.assertEqual(chunk_id(-.1, -256), '-1_-1')
        with tempfile.TemporaryDirectory() as d:
            source = Path(d)/'source'; fixture(source)
            self.assertEqual(len(plan(source, center=[0,0], radius=10)['chunks']), 1)
            for box in ([1,0,0,1], [0,0,float('inf'),1]):
                with self.assertRaises(ValueError): plan(source, bbox=box)
            with self.assertRaises(ValueError): plan(source, center=[0,0], radius=-1)
