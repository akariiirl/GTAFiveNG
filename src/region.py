"""Incremental, source-only region builds from already exported CodeWalker XML.

This does not extract archives or infer update/DLC precedence. A content fingerprint
covers every input and Python pipeline module; outputs are verified before reuse.
"""
import argparse
import contextlib
import hashlib
import io
import json
import math
from pathlib import Path
from convert import build
from selection import selection
from package import package, validate


def fingerprints(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()}


def region_id(center=None, radius=None, bbox=None):
    return 'region-' + hashlib.sha256(json.dumps(selection(center, radius, bbox), sort_keys=True).encode()).hexdigest()[:16]


def run(source, workspace, center=None, radius=None, maps=True, bbox=None):
    source, workspace = Path(source).resolve(), Path(workspace).resolve()
    if not source.is_dir():
        raise ValueError('Exported source directory does not exist')
    if workspace == source or source in workspace.parents or workspace in source.parents:
        raise ValueError('Keep source and workspace directories separate')
    config = selection(center, radius, bbox)
    inputs = fingerprints(source)
    if not any(n.endswith('.ymap.xml') for n in inputs):
        raise ValueError('No exported YMAP XML found')
    pipeline = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}
    signature = {'schema': 1, 'selection': config, 'inputs': inputs, 'pipeline': pipeline, 'maps': maps}
    digest = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()
    target = workspace / region_id(center, radius, bbox) / digest
    manifest = target / 'region-manifest.json'
    if manifest.exists():
        prior = json.loads(manifest.read_text())
        if prior['signature'] != signature or prior['outputs'] != {k:v for k,v in fingerprints(target).items() if k != manifest.name}:
            raise ValueError('Cached output changed; preserve it and choose a fresh workspace')
        validate(target / 'build')
        return target
    if target.exists():
        raise FileExistsError('Incomplete previous build preserved: ' + str(target))
    target.mkdir(parents=True)
    with contextlib.redirect_stdout(io.StringIO()):
        report = build(source, target / 'build', center, radius, bbox=bbox)
        validate(target / 'build')
        package(target / 'build', target / 'region.zip')
        if maps and report['visual_instances']:
            from progress_maps import generate
            generate(target / 'build', source, target / 'progress', region_id(center, radius, bbox))
    manifest.write_text(json.dumps({'signature': signature, 'outputs': fingerprints(target),
                                    'in_game_verified': False}, indent=2))
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--center', type=float, nargs=2)
    parser.add_argument('--radius', type=float)
    parser.add_argument('--bbox', nargs=4, type=float)
    parser.add_argument('--no-maps', action='store_true')
    args = parser.parse_args()
    print(run(args.source, args.workspace, args.center, args.radius, not args.no_maps, bbox=args.bbox))
