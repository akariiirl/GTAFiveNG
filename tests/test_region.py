"""Original tiny fixtures: no game-derived geometry, textures or metadata."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from region import run, region_id, selection
from package import validate, package


def fixture(source):
    source.mkdir()
    (source/'toy.ydr.xml').write_text('''<Drawable><ShaderGroup><Shaders><Item><Name>default</Name><FileName>default</FileName><Parameters><Item name="DiffuseSampler"><Name>missing_paint</Name></Item></Parameters></Item></Shaders></ShaderGroup><DrawableModelsHigh><Item><Geometries><Item><ShaderIndex value="0"/><VertexBuffer><Layout><Position/></Layout><Data>0 0 0
4 0 0
0 4 0</Data></VertexBuffer><IndexBuffer><Data>0 1 2</Data></IndexBuffer></Item></Geometries></Item></DrawableModelsHigh></Drawable>''')
    def entity(name, x):
        return f'<Item><archetypeName>{name}</archetypeName><position x="{x}" y="0" z="0"/><rotation x="0" y="0" z="0" w="1"/><lodLevel>LODTYPES_DEPTH_HD</lodLevel></Item>'
    (source/'toy.ymap.xml').write_text('<CMapData><entities>'+entity('toy', 0)+entity('toy', 10)+entity('toy', 11)+entity('absent', 1)+'</entities></CMapData>')


class RegionTests(unittest.TestCase):
    def test_selection(self):
        self.assertEqual(region_id([0, -0.0], 10), region_id([0., 0.], 10.))
        for radius in (0, -1, float('nan'), float('inf')):
            with self.assertRaises(ValueError): selection([0, 0], radius)

    def test_end_to_end_and_cache(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); source = root/'source'; fixture(source)
            output = run(source, root/'work', [0, 0], 10, maps=False)
            report = json.loads((output/'build/conversion_report.json').read_text())
            self.assertEqual(report['visual_instances'], 2)  # inclusive radius
            self.assertEqual(report['missing_assets'], ['absent'])
            self.assertEqual(report['missing_textures'], ['missing_paint'])
            self.assertEqual(report['visual_triangles'], 2)
            self.assertEqual(run(source, root/'work', [0, 0], 10, maps=False), output)
            with contextlib.redirect_stdout(io.StringIO()):
                package(output/'build', root/'second.zip')
            self.assertEqual((output/'region.zip').read_bytes(), (root/'second.zip').read_bytes())
            with self.assertRaises(FileExistsError): package(output/'build', root/'second.zip')
            (source/'toy.ydr.xml').write_text((source/'toy.ydr.xml').read_text().replace('4 0 0', '5 0 0'))
            changed = run(source, root/'work', [0, 0], 10, maps=False)
            self.assertNotEqual(changed, output)
            (changed/'region.zip').write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError, 'Cached output changed'):
                run(source, root/'work', [0, 0], 10, maps=False)
            next((output/'build/levels').rglob('toy.dae')).unlink()
            with self.assertRaisesRegex(ValueError, 'Missing shape'): validate(output/'build')

    def test_maps_preserve_milestones(self):
        from progress_maps import generate
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            root = Path(d); fixture(root/'source')
            output = run(root/'source', root/'work', [0, 0], 10)
            progress = output/'progress'
            original = {p: p.read_bytes() for p in progress.rglob('*.png')}
            summary = generate(output/'build', root/'source', progress, 'synthetic-second')
            self.assertIsNone(summary['whole_island_exported_area_percent'])
            self.assertEqual(summary['asset_completeness']['expected_instances_in_available_selected_ymaps'], 3)
            self.assertEqual(summary['asset_completeness']['missing_placements'], 1)
            import os, shutil
            artifact=os.environ.get('SYNTHETIC_ARTIFACT_DIR')
            if artifact:
                destination=Path(artifact); destination.mkdir(parents=True,exist_ok=True)
                for name in ('asset_density.png','neighborhood_progress.png','conversion_heatmap.png','progress_summary.json'):
                    shutil.copyfile(progress/name,destination/('synthetic_'+name))
            for p, data in original.items():
                if p.parent != progress: self.assertEqual(p.read_bytes(), data)

    def test_source_protection(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d)/'source'; fixture(source)
            with self.assertRaises(ValueError): run(source, source/'output', [0,0], 10)
