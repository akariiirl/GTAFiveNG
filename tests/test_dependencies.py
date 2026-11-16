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

    def test_dictionary_fragment_priorities_and_alias_cycles(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'pack.ydd.xml').write_text('<DrawableDictionary><Item><Name>toy</Name></Item></DrawableDictionary>')
            (root/'toy.yft.xml').write_text('<Fragment><Drawable/></Fragment>')
            (root/'aliases.ytyp.xml').write_text('<CMapTypes><archetypes><Item><name>a</name><assetName>b</assetName></Item><Item><name>b</name><assetName>toy</assetName></Item><Item><name>x</name><assetName>y</assetName></Item><Item><name>y</name><assetName>x</assetName></Item></archetypes></CMapTypes>')
            self.assertNotIn('toy', resolve(root)[0])
            (root/'dependency-policy.json').write_text(json.dumps({'priorities': {'pack.ydd.xml': 5}}))
            resolved, report = resolve(root)
            self.assertEqual(resolved['a'], (root/'pack.ydd.xml', 'toy'))
            self.assertNotIn('x', resolved)
            self.assertEqual(report['provenance']['toy']['selected'], 'pack.ydd.xml#toy')

    def test_texture_scope_missing_cycles_and_escape(self):
        from dependencies import texture_lookup
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root/'paint.synthetic').write_bytes(b'original test data')
            policy = {'txd_parents': {'child': 'parent'}, 'textures': {'parent': {'paint': 'paint.synthetic'}}}
            self.assertEqual(texture_lookup(root, 'child', 'paint', policy)[0], (root/'paint.synthetic').resolve())
            self.assertIsNone(texture_lookup(root, 'other', 'paint', policy)[0])
            policy['txd_parents']['parent'] = 'child'
            self.assertIn('cycle', texture_lookup(root, 'child', 'missing', policy)[1])
            policy['textures']['child'] = {'paint': '../outside'}
            with self.assertRaises(ValueError): texture_lookup(root, 'child', 'paint', policy)

    def test_ydd_member_conversion(self):
        from test_region import fixture
        from region import run
        import json
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); source = root/'source'; fixture(source)
            drawable = (source/'toy.ydr.xml').read_text().replace('<Drawable>', '<Item><Name>toy</Name>').replace('</Drawable>', '</Item>')
            (source/'toy.ydr.xml').unlink()
            (source/'pack.ydd.xml').write_text('<DrawableDictionary>'+drawable+'</DrawableDictionary>')
            target = run(source, root/'work', [0,0], 10, maps=False)
            self.assertEqual(json.loads((target/'build/conversion_report.json').read_text())['visual_instances'], 2)

    def test_scoped_texture_packaging(self):
        import json
        import struct
        from test_region import fixture
        from region import run
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); source = root/'source'; fixture(source)
            header = bytearray(128); header[:4] = b'DDS '
            struct.pack_into('<II',header,12,1,1)
            struct.pack_into('<I',header,80,2); struct.pack_into('<I',header,88,8)
            (source/'parent.dds').write_bytes(header + b'\x80')
            (source/'other.dds').write_bytes(header + b'\xff')
            drawable = (source/'toy.ydr.xml').read_text()
            (source/'second.ydr.xml').write_text(drawable)
            placement = (source/'toy.ymap.xml').read_text().replace('<archetypeName>absent</archetypeName>','<archetypeName>second</archetypeName>')
            (source/'toy.ymap.xml').write_text(placement)
            policy = {'scoped_textures':True, 'asset_txds':{'toy':'child','second':'other'},
                      'txd_parents':{'child':'parent'},
                      'textures':{'parent':{'missing_paint':'parent.dds'},'other':{'missing_paint':'other.dds'}}}
            (source/'dependency-policy.json').write_text(json.dumps(policy))
            target = run(source, root/'work', [0,0], 10, maps=False)
            report = json.loads((target/'build/conversion_report.json').read_text())
            self.assertEqual(report['missing_textures'], [])
            self.assertEqual(report['textures'], 2)
            materials = json.loads((target/'build/levels/los_santos_fazes/art/main.materials.json').read_text())
            first = materials['lsf_toy_0']['Stages'][0]['diffuseMap']
            second = materials['lsf_second_0']['Stages'][0]['diffuseMap']
            self.assertNotEqual(first, second)
            self.assertNotEqual((target/'build'/first.lstrip('/')).read_bytes(),(target/'build'/second.lstrip('/')).read_bytes())
