import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from dependencies import resolve


class DependencyTests(unittest.TestCase):
    def test_alias_and_ambiguity(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'base.rpf_toy.ydr.xml').write_text('<Drawable/>')
            (root/'toy.ytyp.xml').write_text('<CMapTypes><archetypes><Item><name>placement</name><assetName>toy</assetName></Item></archetypes></CMapTypes>')
            resolved, report = resolve(root)
            self.assertEqual(resolved['placement'], resolved['toy'])
            (root/'update.rpf_toy.ydr.xml').write_text('<Drawable/>')
            resolved, report = resolve(root)
            self.assertNotIn('toy', resolved)
            self.assertNotIn('placement', resolved)
            self.assertEqual(len(report['ambiguous_drawables']['toy']), 2)
            resolved, _ = resolve(root, {'toy': 'update.rpf_toy.ydr.xml'})
            self.assertEqual(resolved['placement'].name, 'update.rpf_toy.ydr.xml')
            with self.assertRaises(ValueError): resolve(root, {'toy': 'bogus'})
