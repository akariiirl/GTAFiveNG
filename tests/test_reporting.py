import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from reporting import compare, METRICS


class ReportingTests(unittest.TestCase):
    def test_immutable_comparison_and_unknowns(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name, value in [('a',1),('b',2)]:
                directory = root/name; directory.mkdir()
                report = {k:value for k in METRICS}
                report.update(missing_assets=['toy']*value, missing_textures=[], origin=[0,0,0], radius=10)
                (directory/'conversion_report.json').write_text(json.dumps(report))
            output = root/'comparison'
            result = compare(root/'a', root/'b', output)
            self.assertEqual(result['delta']['visual_instances'],1)
            self.assertIsNone(result['whole_island_completion_percent'])
            self.assertTrue(result['same_selection'])
            self.assertTrue((output/'comparison.png').read_bytes().startswith(b'\x89PNG'))
            with self.assertRaises(FileExistsError): compare(root/'a',root/'b', output)
            artifact = os.environ.get('SYNTHETIC_ARTIFACT_DIR')
            if artifact:
                import shutil
                destination = Path(artifact); destination.mkdir(parents=True,exist_ok=True)
                for file in output.iterdir(): shutil.copyfile(file,destination/file.name)
