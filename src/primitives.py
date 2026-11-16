"""Convex collision primitive tessellation in source coordinates."""
import math
import numpy as np

def rounded_shape(p1,p2,radius,kind,sides=8,hemisphere_steps=3):
    p1=np.asarray(p1,dtype=float); p2=np.asarray(p2,dtype=float)
    if radius<=0 or not math.isfinite(radius): raise ValueError('Invalid primitive radius')
    delta=p2-p1; length=np.linalg.norm(delta)
    axis=delta/length if length>1e-9 else np.array([0.,0.,1.])
    helper=np.array([1.,0.,0.]) if abs(axis[0])<0.9 else np.array([0.,1.,0.])
    x=np.cross(axis,helper); x/=np.linalg.norm(x); y=np.cross(axis,x)
    if kind=='Cylinder': rings=[(p1,0),(p1,radius),(p2,radius),(p2,0)]
    else:
        rings=[]
        for i in range(hemisphere_steps+1):
            a=-math.pi/2+i*math.pi/(2*hemisphere_steps)
            rings.append((p1+axis*radius*math.sin(a),radius*math.cos(a)))
        for i in range(hemisphere_steps+1):
            a=i*math.pi/(2*hemisphere_steps)
            if i==0 and length<1e-9: continue
            rings.append((p2+axis*radius*math.sin(a),radius*math.cos(a)))
    vertices=np.array([center+r*(math.cos(2*math.pi*j/sides)*x+math.sin(2*math.pi*j/sides)*y) for center,r in rings for j in range(sides)])
    faces=[]
    for i in range(len(rings)-1):
        for j in range(sides):
            a=i*sides+j; b=i*sides+(j+1)%sides; c=(i+1)*sides+j; d=(i+1)*sides+(j+1)%sides
            faces.extend([[a,b,c],[b,d,c]])
    faces=np.array(faces)
    t=vertices[faces]; normals=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0])
    keep=np.linalg.norm(normals,axis=1)>1e-12; faces=faces[keep]; normals=normals[keep]
    reverse=np.sum(normals*(vertices[faces].mean(axis=1)-(p1+p2)/2),axis=1)<0
    faces[reverse]=faces[reverse,::-1]
    return vertices,faces
