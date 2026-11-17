"""Compare sampled original visual road surfaces against converted collision triangles."""
from pathlib import Path
import argparse,json,math
import xml.etree.ElementTree as ET
import numpy as np
from collections import defaultdict

NS={'c':'http://www.collada.org/2005/11/COLLADASchema'}

def is_drivable_road(name):
    return name.startswith('sc1_rd_r') and 'shadow' not in name.lower()

def triangles(path):
    root=ET.parse(path)
    for mesh in root.findall('.//c:geometry/c:mesh',NS):
        vertices=mesh.find('c:vertices/c:input',NS).get('source')[1:]
        source=mesh.find(f"c:source[@id='{vertices}']/c:float_array",NS)
        v=np.fromstring(source.text,sep=' ').reshape(-1,3)
        for tri in mesh.findall('c:triangles',NS):
            idx=np.fromstring(tri.findtext('c:p',namespaces=NS),sep=' ',dtype=int).reshape(-1,3)
            yield v[idx]

def validate(root,step=50,output=None):
    if not isinstance(step, int) or step <= 0: raise ValueError('Sample step must be a positive integer')
    root=Path(root); level=root/'levels/los_santos_fazes'
    alltri=[]
    for p in sorted((level/'art/shapes').glob('collision*.dae')):
        alltri.extend(triangles(p))
    t=np.concatenate(alltri) if alltri else np.empty((0,3,3)); a=t[:,0]; b=t[:,1]-a; c=t[:,2]-a
    den=b[:,0]*c[:,1]-b[:,1]*c[:,0]
    keep=np.abs(den)>1e-8; t=t[keep]; a=a[keep]; b=b[keep]; c=c[keep]; den=den[keep]
    cells=defaultdict(list); size=16
    low=np.floor(t[:,:,:2].min(axis=1)/size).astype(int); high=np.floor(t[:,:,:2].max(axis=1)/size).astype(int)
    for i,(lo,hi) in enumerate(zip(low,high)):
        for x in range(lo[0],hi[0]+1):
            for y in range(lo[1],hi[1]+1): cells[x,y].append(i)
    def heights(x,y):
        ids=np.asarray(cells.get((math.floor(x/size),math.floor(y/size)),[]),dtype=int)
        d=np.array([x,y])-a[ids,:2]
        u=(d[:,0]*c[ids,1]-d[:,1]*c[ids,0])/den[ids]
        v=(b[ids,0]*d[:,1]-b[ids,1]*d[:,0])/den[ids]
        inside=(u>=-1e-6)&(v>=-1e-6)&(u+v<=1+1e-6)
        return (a[ids,2]+u*b[ids,2]+v*c[ids,2])[inside]
    samples=[]
    objects=[json.loads(l) for l in (level/'main/MissionGroup/Geometry/items.level.json').read_text().splitlines()]
    for obj in objects:
        name=obj.get('sourceArchetype',Path(obj.get('shapeName','')).stem)
        if not is_drivable_road(name) or obj.get('collisionType')!='None': continue
        transform=np.array(obj['rotationMatrix']).reshape(3,3)
        for local in triangles(root/obj['shapeName'].lstrip('/')):
            world=(local*np.array(obj['scale']))@transform+np.array(obj['position'])
            normal=np.cross(world[:,1]-world[:,0],world[:,2]-world[:,0])
            norm=np.linalg.norm(normal,axis=1)
            good=(norm>2)&(normal[:,2]>norm*0.85)
            for pos in world[good].mean(axis=1)[::step]:
                z=heights(*pos[:2]); delta=float(np.min(np.abs(z-pos[2]))) if len(z) else None
                samples.append({'asset':name,'position':pos.tolist(),'height_error':delta})
    failures=[s for s in samples if s['height_error'] is None or s['height_error']>0.5]
    result={'collision_triangles':len(t),'collision_evidence_available':bool(len(t)),'sample_count':len(samples),'within_half_meter':len(samples)-len(failures),'failures':failures,'method':'Upward visual road triangle centroids, sampled at fixed stride per submesh; compare all collision hits in XY. This is not exhaustive gap detection or an in-game vehicle test.'}
    Path(output or root/'surface_validation.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='failures'},indent=2))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('root'); p.add_argument('--step',type=int,default=50)
    args=p.parse_args(); validate(args.root,args.step)
