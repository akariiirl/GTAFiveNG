"""Compare exported YBN geometry in world coordinates; no game precedence inferred."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import numpy as np
from convert import bounds_mesh


def triangle_keys(triangles, decimals=5):
    return {tuple(sorted(tuple(v) for v in t)) for t in np.round(triangles,decimals)}


def height_hits(triangles, xy):
    a=triangles[:,0]; b=triangles[:,1]-a; c=triangles[:,2]-a
    den=b[:,0]*c[:,1]-b[:,1]*c[:,0]; keep=np.abs(den)>1e-9
    a,b,c,den=a[keep],b[keep],c[keep],den[keep]
    d=np.asarray(xy)-a[:,:2]
    u=(d[:,0]*c[:,1]-d[:,1]*c[:,0])/den
    v=(b[:,0]*d[:,1]-b[:,1]*d[:,0])/den
    inside=(u>=-1e-6)&(v>=-1e-6)&(u+v<=1+1e-6)
    return a[inside,2]+u[inside]*b[inside,2]+v[inside]*c[inside,2]


def load(path):
    report={'unsupported_collision':Counter(),'degenerate_triangles_removed':0}
    meshes=bounds_mesh(path,np.zeros(3),report)
    triangles=np.concatenate([m['v'][m['i']] for m in meshes]) if meshes else np.empty((0,3,3))
    return path,triangles,report


def compare(paths):
    with ThreadPoolExecutor(max_workers=2) as pool: data=list(pool.map(load,paths))
    files=[]; pairs=[]
    for path,t,r in data:
        files.append({'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'triangles':len(t),'bounds':[t.min(axis=(0,1)).tolist(),t.max(axis=(0,1)).tolist()] if len(t) else None,'diagnostics':r})
    for i,(p,a,_) in enumerate(data):
        for q,b,_ in data[i+1:]:
            if p.name.split('.rpf_')[-1]!=q.name.split('.rpf_')[-1]: continue
            ka,kb=triangle_keys(a),triangle_keys(b); errors=[]; misses=0
            normal=np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0]); norm=np.linalg.norm(normal,axis=1)
            roadlike=a[(norm>1e-8)&(np.abs(normal[:,2])>norm*0.85)]
            samples=roadlike.mean(axis=1)[::max(1,len(roadlike)//400)]
            for point in samples:
                hits=height_hits(b,point[:2])
                if len(hits): errors.append(float(np.min(np.abs(hits-point[2]))))
                else: misses+=1
            pairs.append({'a':p.name,'b':q.name,'common_triangles_rounded_1e5':len(ka&kb),'only_a':len(ka-kb),'only_b':len(kb-ka),'samples':len(samples),'missing_hits':misses,'max_height_difference':max(errors,default=None),'over_half_meter':sum(x>0.5 for x in errors)})
    return {'method':'Converted world-space triangles including composite transforms; rounded geometry set comparison and sampled XY height queries. Not a runtime test.','files':files,'pairs':pairs}


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('source',type=Path); p.add_argument('output',type=Path); a=p.parse_args()
    result=compare(sorted(a.source.glob('*.ybn.xml')))
    with a.output.open('x') as f: json.dump(result,f,indent=2)
