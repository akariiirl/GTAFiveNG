"""Shared region selection in original GTA XY metres; inclusive placement bounds."""
import math


def selection(center=None, radius=None, bbox=None):
    if bbox is not None:
        if center is not None or radius is not None:
            raise ValueError('Use bounding box or center/radius, not both')
        box = [float(v) + 0.0 for v in bbox]
        if len(box) != 4 or not all(math.isfinite(v) for v in box) or box[0] >= box[2] or box[1] >= box[3]:
            raise ValueError('Use finite xmin ymin xmax ymax with positive width and height')
        return {'bbox': box}
    if center is None or radius is None: raise ValueError('Center and radius required')
    center = [float(v) + 0.0 for v in center]; radius = float(radius)
    if len(center) != 2 or not all(math.isfinite(v) for v in [*center,radius]) or radius <= 0:
        raise ValueError('Use a finite XY center and positive radius')
    return {'center': center, 'radius': radius}


def contains(config, xy):
    if 'regions' in config: return any(contains(region,xy) for region in config['regions'])
    x,y = map(float, xy)
    if not math.isfinite(x) or not math.isfinite(y): raise ValueError('Nonfinite placement')
    if 'bbox' in config:
        a,b,c,d = config['bbox']
        return a <= x <= c and b <= y <= d
    return math.hypot(x-config['center'][0],y-config['center'][1]) <= config['radius']


def frame(config):
    if 'bbox' in config:
        a,b,c,d = config['bbox']
        return [(a+c)/2,(b+d)/2], math.hypot(c-a,d-b)/2, [c-a,d-b]
    radius = config['radius']
    return config['center'], radius, [radius*2,radius*2]
