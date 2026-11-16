"""Experimental deterministic visual LOD previews. Never simplify physics meshes.

Vertex clustering preserves boundary vertices and duplicate-position seam vertices.
An orientation reversal or empty result falls back to the original. These guards
are not a proof of topology, UV fidelity, Hausdorff error or in-game suitability.
"""
import math
import numpy as np


def simplify(mesh, cell_size):
    if not math.isfinite(cell_size) or cell_size<=0: raise ValueError('Positive finite LOD cell size required')
    vertices=np.asarray(mesh['v'],dtype=float); faces=np.asarray(mesh['i'],dtype=int)
    if vertices.ndim!=2 or vertices.shape[1]!=3 or faces.ndim!=2 or faces.shape[1]!=3 or not np.isfinite(vertices).all(): raise ValueError('Invalid LOD mesh')
    if faces.size and (faces.min()<0 or faces.max()>=len(vertices)): raise ValueError('Invalid LOD indices')
    report={'cell_size_m':cell_size,'input_triangles':len(faces),'output_triangles':len(faces),'max_vertex_displacement_m':0.,'fallback':None}
    if not len(faces): return dict(mesh),report
    edges=np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1)
    edges,counts=np.unique(edges,axis=0,return_counts=True)
    protected=np.zeros(len(vertices),dtype=bool); protected[np.unique(edges[counts==1])]=True
    _,positions,counts=np.unique(vertices,axis=0,return_inverse=True,return_counts=True)
    protected|=counts[positions]>1
    cells=np.floor(vertices/cell_size)
    if not np.isfinite(cells).all() or np.abs(cells).max()>2**60: raise ValueError('LOD cell scale out of range')
    keys=np.column_stack([cells.astype(np.int64),np.where(protected,np.arange(len(vertices)),-1)])
    _,groups=np.unique(keys,axis=0,return_inverse=True); count=np.bincount(groups)
    def average(values):
        result=np.zeros((len(count),values.shape[1])); np.add.at(result,groups,values)
        return result/count[:,None]
    clustered=average(vertices); mapped=groups[faces]
    old=vertices[faces]; new=clustered[mapped]
    old_normal=np.cross(old[:,1]-old[:,0],old[:,2]-old[:,0]); new_normal=np.cross(new[:,1]-new[:,0],new[:,2]-new[:,0])
    keep=np.linalg.norm(new_normal,axis=1)>1e-9
    if np.any(np.sum(old_normal[keep]*new_normal[keep],axis=1)<=0):
        report['fallback']='orientation change'; return dict(mesh),report
    mapped=mapped[keep]
    if not len(mapped): report['fallback']='empty result'; return dict(mesh),report
    _,first=np.unique(np.sort(mapped,axis=1),axis=0,return_index=True); mapped=mapped[np.sort(first)]
    used,indices=np.unique(mapped,return_inverse=True)
    output={**mesh,'v':clustered[used],'i':indices.reshape(-1,3)}
    for field in ('n','uv'):
        if mesh.get(field) is None: continue
        values=np.asarray(mesh[field],dtype=float)
        if len(values)!=len(vertices) or values.ndim!=2 or not np.isfinite(values).all(): raise ValueError('Invalid LOD attributes')
        result=average(values)[used]
        if field=='n': result/=np.maximum(np.linalg.norm(result,axis=1,keepdims=True),1e-12)
        output[field]=result
    report['output_triangles']=len(mapped)
    report['max_vertex_displacement_m']=float(np.linalg.norm(clustered[groups]-vertices,axis=1).max())
    return output,report


def validate_settings(sizes, collision_limit):
    if any(not math.isfinite(v) or v<=0 for v in sizes) or list(sizes)!=sorted(set(sizes)): raise ValueError('LOD sizes must be increasing positive finite values')
    if collision_limit is not None and (not isinstance(collision_limit,int) or isinstance(collision_limit,bool) or collision_limit<0): raise ValueError('Collision triangle limit must be a nonnegative integer')
