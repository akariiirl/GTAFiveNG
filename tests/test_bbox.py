import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from test_region import fixture
from region import run, region_id
from planning import plan
from selection import selection, contains


class BoundingBoxTests(unittest.TestCase):
    def test_export_plan_map_and_cache_agree(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            root = Path(d); source = root/'source'; fixture(source)
            box = [0,-1,10,1]
            target = run(source,root/'work',bbox=box)
            report = json.loads((target/'build/conversion_report.json').read_text())
            self.assertEqual(report['visual_instances'],2)
            self.assertEqual(report['origin'],[5,0,0])
            self.assertEqual(report['selection'],{'bbox':box})
            summary = json.loads((target/'progress/progress_summary.json').read_text())
            self.assertEqual(summary['asset_completeness']['expected_instances_in_available_selected_ymaps'],3)
            self.assertEqual(summary['asset_completeness']['missing_placements'],1)
            self.assertEqual(summary['selection'],report['selection'])
            self.assertEqual(plan(source,bbox=box)['selection'],report['selection'])
            self.assertEqual(run(source,root/'work',bbox=box),target)
            self.assertNotEqual(region_id(bbox=box),region_id([5,0],report['radius']))
            info = json.loads((target/'build/levels/los_santos_fazes/info.json').read_text())
            self.assertEqual(info['size'],[10,2])

    def test_invalid_and_inclusive_selection(self):
        config = selection(bbox=[-1,-2,3,4])
        self.assertTrue(contains(config,[-1,-2])); self.assertTrue(contains(config,[3,4]))
        self.assertFalse(contains(config,[3.01,4]))
        for box in ([0,0,0,1],[0,0,1,float('nan')],[1,0,0,1]):
            with self.assertRaises(ValueError): selection(bbox=box)
        with self.assertRaises(ValueError): selection([0,0],1,bbox=[0,0,1,1])
