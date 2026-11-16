"""Offline predictive chunk planner. Estimates only; no BeamNG calls."""
import math


def plan(chunks, position, speed, heading, *, lookahead=3.0, radius=256.0,
         hysteresis=64.0, previous=(), load_budget=8):
    if len(position) != 2 or not all(math.isfinite(x) for x in (*position, speed, heading, lookahead, radius, hysteresis)):
        raise ValueError('Finite position and motion parameters required')
    if speed < 0 or lookahead < 0 or radius < 0 or hysteresis < 0 or load_budget < 0:
        raise ValueError('Negative speed, distance, or budget')
    hx, hy = math.cos(heading), math.sin(heading)
    predicted = (position[0] + hx * speed * lookahead, position[1] + hy * speed * lookahead)
    previous = set(previous)
    visual, collision, distances = set(), set(), {}
    for key, item in chunks.items():
        box = item['bounds']
        if len(box) != 4 or not all(math.isfinite(v) for v in box) or box[0] > box[2] or box[1] > box[3]:
            raise ValueError('Invalid chunk bounds: ' + key)
        def distance(point):
            near = (max(box[0], min(point[0], box[2])), max(box[1], min(point[1], box[3])))
            return math.dist(point, near)
        d = min(distance(position), distance(predicted))
        distances[key] = d
        if d <= radius or (key in previous and distance(position) <= radius + hysteresis):
            visual.add(key)
            if item.get('collision_available') is True:
                collision.add(key)
    # Explicit dependency closure; missing targets are reported, never fabricated.
    missing, visiting = set(), set()
    def close(key):
        if key in visiting: raise ValueError('Chunk dependency cycle: ' + key)
        visiting.add(key)
        for dep in chunks[key].get('dependencies', ()):
            if dep not in chunks: missing.add(dep)
            elif dep not in visual:
                visual.add(dep); close(dep)
        visiting.remove(key)
    for key in tuple(sorted(visual)): close(key)
    ordered = sorted(visual, key=lambda k: (distances.get(k, 0), k))
    loads = [k for k in ordered if k not in previous][:load_budget]
    deferred = [k for k in ordered if k not in previous and k not in loads]
    # Keep previous chunks through a conservative radius+grace envelope.
    unload = sorted(k for k in previous if k not in visual and k in chunks and distances.get(k, math.inf) > radius + hysteresis)
    return {'predicted_xy': predicted, 'visual_chunks': sorted(visual), 'collision_ready': sorted(collision),
            'drivable_chunks': [], 'load_now': loads, 'deferred': deferred, 'unload': unload,
            'missing_dependencies': sorted(missing), 'distance': distances,
            'label': 'SYNTHETIC SCHEDULER PLAN; collision readiness means inventory flag only, not drivable'}
