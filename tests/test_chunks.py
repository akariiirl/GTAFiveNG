import hashlib
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from chunks import Residency, lod_level, visible_chunks


class ChunkTests(unittest.TestCase):
    def test_shared_refs_unload_reload_and_determinism(self):
        data = {hashlib.sha256(v).hexdigest(): v for v in (b'shared', b'a', b'b')}
        shared, a, b = [hashlib.sha256(v).hexdigest() for v in (b'shared', b'a', b'b')]
        loads = []
        def loader(key): loads.append(key); return data[key]
        cache = Residency({'b':[shared,b], 'a':[a,shared]}, 20)
        cache.transition(['b','a'], loader)
        self.assertEqual(cache.bytes_used, 8)
        self.assertEqual(cache.references[shared], 2)
        snapshot = cache.manifest()
        cache.transition(['a','b'], loader)
        self.assertEqual(cache.manifest(), snapshot)
        self.assertEqual(len(loads), 3)
        cache.transition(['b'], loader)
        self.assertNotIn(a, cache.resources)
        self.assertEqual(cache.references[shared], 1)
        cache.transition([], loader)
        self.assertEqual(cache.bytes_used, 0)
        cache.transition(['a'], loader)
        self.assertEqual(len(loads), 5)

    def test_missing_corrupt_and_over_budget_are_atomic(self):
        payload = b'abc'; key = hashlib.sha256(payload).hexdigest()
        cache = Residency({'a':[key]}, 2)
        with self.assertRaises(MemoryError): cache.transition(['a'], lambda _:payload)
        self.assertEqual(cache.bytes_used, 0)
        with self.assertRaises(ValueError): cache.transition(['a'], lambda _:b'changed')
        with self.assertRaises(KeyError): cache.transition(['missing'], lambda _:payload)
        self.assertEqual(cache.active, ())

    def test_visibility_and_lod_boundaries(self):
        self.assertEqual(visible_chunks({'near':[0,0,10,10], 'far':[20,20,30,30]}, [-1,0], 1), ['near'])
        self.assertEqual([lod_level(d,[10,20]) for d in (0,10,19,20)], [0,1,1,2])
        with self.assertRaises(ValueError): lod_level(1,[20,10])
        with self.assertRaises(ValueError): visible_chunks({}, [float('nan'),0], 1)
