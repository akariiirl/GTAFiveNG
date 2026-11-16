"""Read-only exported-YMAP planner; emits deterministic extraction task manifests."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
from dependencies import resolve


def chunk_id(x, y, size=256):
    if not all(math.isfinite(v) for v in (x, y, size)) or size <= 0:
        raise ValueError('Finite coordinates and positive chunk size required')
    return f'{math.floor(x/size)}_{math.floor(y/size)}'


def plan(source, *, bbox=None, center=None, radius=None, chunk_size=256):
    source = Path(source)
    chunk_id(0, 0, chunk_size)
    if bbox is not None:
        if center is not None or radius is not None or len(bbox) != 4 or not all(math.isfinite(v) for v in bbox) or bbox[0] > bbox[2] or bbox[1] > bbox[3]:
            raise ValueError('Use an ordered finite bounding box or center/radius')
        contains = lambda x,y: bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]
        selection = {'bbox': list(map(float, bbox))}
    else:
        if center is None or len(center) != 2 or radius is None or not all(math.isfinite(v) for v in [*center, radius]) or radius <= 0:
            raise ValueError('Finite center and positive radius required')
        contains = lambda x,y: math.hypot(x-center[0], y-center[1]) <= radius
        selection = {'center': list(map(float, center)), 'radius': float(radius)}
    resources, diagnostics = resolve(source)
    chunks = {}; graph = {}; placements = set()
    for path in sorted(source.glob('*.ymap.xml')):
        if any(n in path.name for n in ('oldbill', 'newbill')): continue
        for item in ET.parse(path).getroot().findall('entities/Item'):
            if item.findtext('lodLevel') not in ('LODTYPES_DEPTH_HD', 'LODTYPES_DEPTH_ORPHANHD'): continue
            position = item.find('position')
            xyz = tuple(float(position.get(k, 0)) for k in 'xyz')
            if not all(math.isfinite(v) for v in xyz): raise ValueError('Nonfinite placement')
            name = item.findtext('archetypeName', '').lower()
            if not contains(*xyz[:2]) or (name, xyz) in placements: continue
            placements.add((name, xyz))
            key = chunk_id(*xyz[:2], chunk_size)
            chunks.setdefault(key, set()).add(name)
            resource = resources.get(name)
            export = resource[0] if isinstance(resource, tuple) else resource
            graph[name] = {'export': export.name if export else None, 'missing': resource is None}
    inputs = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(source.iterdir()) if p.is_file()}
    result = {'schema': 1, 'selection': selection, 'chunk_size': chunk_size,
              'chunks': {k: sorted(v) for k,v in sorted(chunks.items())},
              'dependencies': dict(sorted(graph.items())), 'inputs': inputs,
              'diagnostics': diagnostics, 'in_game_verified': False}
    result['plan_id'] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    return result


def reconcile(plan, source, previous=None):
    """Resume task state only when both plan and exported bytes still match."""
    previous = previous or {}
    same = previous.get('plan_id') == plan['plan_id']
    tasks = {}
    for name, dependency in plan['dependencies'].items():
        export = dependency['export']
        path = Path(source)/export if export else None
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path and path.is_file() else None
        old = previous.get('tasks', {}).get(name, {}) if same else {}
        state = 'verified' if digest and digest == plan['inputs'].get(export) else 'pending'
        tasks[name] = {'state': state, 'sha256': digest,
                       'previous_error': old.get('error') if state == 'pending' else None}
    return {'plan_id': plan['plan_id'], 'tasks': tasks}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--bbox', nargs=4, type=float)
    p.add_argument('--center', nargs=2, type=float)
    p.add_argument('--radius', type=float)
    p.add_argument('--chunk-size', default=256, type=float)
    a = p.parse_args()
    result = plan(a.source, bbox=a.bbox, center=a.center, radius=a.radius, chunk_size=a.chunk_size)
    with a.output.open('x') as stream: json.dump(result, stream, indent=2, sort_keys=True)
