"""Immutable build-count comparisons; no inference of island completion or driving."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

METRICS = ('visual_instances', 'unique_drawables', 'visual_triangles', 'collision_triangles', 'missing_assets', 'missing_textures')


def compare(before, after, output):
    paths = [Path(before)/'conversion_report.json', Path(after)/'conversion_report.json']
    reports = [json.loads(p.read_text()) for p in paths]
    counts = [{key: len(r[key]) if isinstance(r.get(key), list) else r.get(key) for key in METRICS} for r in reports]
    for count in counts:
        if any(not isinstance(v, (int,float)) or not math.isfinite(v) or v < 0 for v in count.values()):
            raise ValueError('Comparison requires nonnegative recorded counts')
    same = all(reports[0].get(k) == reports[1].get(k) for k in ('origin','radius'))
    result = {'schema': 1, 'report_sha256': [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths],
              'same_selection': same, 'before': counts[0], 'after': counts[1],
              'delta': {k: counts[1][k]-counts[0][k] for k in METRICS},
              'whole_island_completion_percent': None, 'verified_drivable_area_m2': None,
              'limitations': ['Counts describe exported inputs only; missing counts are unique names, not placements.',
                             'Different selections or source inventories are not equivalent coverage comparisons.',
                             'Triangle counts do not establish driving quality or gameplay performance.']}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    figure, axes = plt.subplots(2, 3, figsize=(12, 7))
    for axis, key in zip(axes.flat, METRICS):
        axis.bar(['Before', 'After'], [counts[0][key], counts[1][key]], color=['#64748b','#248de5'])
        axis.set_title(key.replace('_',' ')); axis.set_ylim(bottom=0)
    figure.suptitle('Export evidence comparison | '+('same selection' if same else 'DIFFERENT selections'))
    figure.text(.02,.01,'Island completion and verified driving coverage: unknown. Counts are not gameplay evidence.')
    figure.tight_layout(rect=[0,.04,1,.94]); figure.savefig(output/'comparison.png', dpi=120); plt.close(figure)
    (output/'comparison.json').write_text(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path); parser.add_argument('after', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); compare(args.before, args.after, args.output)
