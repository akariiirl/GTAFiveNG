import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from batch import run_batch
from region import run
from test_region import fixture


class BatchTests(unittest.TestCase):
    def test_shared_resources_packages_and_resume(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            root=Path(d); source=root/'source'; fixture(source)
            regions=[{'center':[0,0],'radius':10},{'bbox':[0,-1,10,1]}]
            destination=run_batch(source,root/'work',regions,maps=False)
            result=json.loads(destination.read_text())
            self.assertEqual(len(result['regions']),2)
            self.assertTrue(result['shared_resources']); self.assertTrue(result['chunks'])
            self.assertIsNone(result['whole_island_completion_percent'])
            previous=destination.stat().st_mtime_ns
            self.assertEqual(run_batch(source,root/'work',regions[::-1],maps=False),destination)
            self.assertEqual(destination.stat().st_mtime_ns,previous)
            self.assertEqual(len(list((root/'work/regions/_shared_drawables').glob('*/*.json'))),1)

    def test_interruption_preserves_completed_regions(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            root=Path(d); source=root/'source'; fixture(source)
            regions=[{'center':[0,0],'radius':10},{'center':[1,0],'radius':10}]
            calls=[]
            def interrupt(*args,**kwargs):
                if calls: raise RuntimeError('Synthetic interruption')
                result=run(*args,**kwargs); calls.append(result); return result
            with self.assertRaises(RuntimeError): run_batch(source,root/'work',regions,maps=False,converter=interrupt)
            first=calls[0]/'region.zip'; previous=first.stat().st_mtime_ns
            destination=run_batch(source,root/'work',regions,maps=False)
            self.assertTrue(destination.exists()); self.assertEqual(first.stat().st_mtime_ns,previous)
            with self.assertRaises(ValueError): run_batch(source,root/'empty',[],maps=False)

    def test_streamed_zip_preserves_legacy_bytes(self):
        import zipfile
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            root=Path(d); source=root/'source'; fixture(source)
            target=run(source,root/'work',[0,0],10,maps=False)
            with zipfile.ZipFile(root/'legacy.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
                for path in sorted((target/'build/levels').rglob('*')):
                    if not path.is_file(): continue
                    info=zipfile.ZipInfo(path.relative_to(target/'build').as_posix(),date_time=(2026,11,15,0,0,0))
                    info.compress_type=zipfile.ZIP_DEFLATED
                    archive.writestr(info,path.read_bytes())
            self.assertEqual((root/'legacy.zip').read_bytes(),(target/'region.zip').read_bytes())
