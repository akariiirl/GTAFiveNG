"""Offline chunk residency model; no BeamNG runtime streaming integration.

Resources are immutable bytes keyed by content hash. A transition is committed
only if all requested chunks/resources validate and fit the configured byte bound.
The bound covers retained payload bytes, not Python/interpreter/loader overhead.
"""
from collections import Counter
import hashlib
import json
import math


class Residency:
    def __init__(self, chunks, max_bytes):
        if not isinstance(max_bytes, int) or max_bytes < 0: raise ValueError('Invalid byte budget')
        self.chunks = {k: tuple(sorted(set(v))) for k,v in chunks.items()}
        self.max_bytes = max_bytes
        self.active = ()
        self.resources = {}
        self.references = Counter()

    @property
    def bytes_used(self):
        return sum(len(value) for value in self.resources.values())

    def transition(self, requested, loader):
        requested = tuple(sorted(set(requested)))
        missing = set(requested) - self.chunks.keys()
        if missing: raise KeyError('Missing chunks: ' + ', '.join(sorted(missing)))
        refs = Counter(key for chunk in requested for key in self.chunks[chunk])
        staged = {}; size = 0
        for key in sorted(refs):
            value = self.resources.get(key)
            if value is None: value = loader(key)
            if not isinstance(value, bytes) or hashlib.sha256(value).hexdigest() != key:
                raise ValueError('Resource fingerprint mismatch: ' + key)
            size += len(value)
            # Include existing resources while staging new bytes to enforce peak payload bound.
            peak = self.bytes_used + sum(len(v) for k,v in staged.items() if k not in self.resources)
            if key not in self.resources: peak += len(value)
            if max(size, peak) > self.max_bytes: raise MemoryError('Chunk transition exceeds payload budget')
            staged[key] = value
        self.active, self.resources, self.references = requested, staged, refs

    def manifest(self):
        return json.dumps({'schema': 1, 'chunks': {k: list(v) for k,v in sorted(self.chunks.items())},
                           'active': list(self.active), 'references': dict(sorted(self.references.items())),
                           'payload_bytes': self.bytes_used, 'runtime_verified': False}, sort_keys=True, separators=(',', ':'))


def visible_chunks(bounds, center, radius):
    if len(center) != 2 or not all(math.isfinite(v) for v in [*center, radius]) or radius < 0:
        raise ValueError('Invalid visibility region')
    result = []
    for key, box in sorted(bounds.items()):
        if len(box) != 4 or not all(math.isfinite(v) for v in box) or box[0] > box[2] or box[1] > box[3]:
            raise ValueError('Invalid chunk bounds')
        nearest = [max(box[i], min(center[i], box[i+2])) for i in range(2)]
        if math.dist(nearest, center) <= radius: result.append(key)
    return result


def lod_level(distance, thresholds):
    if not math.isfinite(distance) or distance < 0 or any(not math.isfinite(v) or v <= 0 for v in thresholds) or list(thresholds) != sorted(set(thresholds)):
        raise ValueError('Use increasing positive LOD thresholds and finite distance')
    return sum(distance >= value for value in thresholds)
