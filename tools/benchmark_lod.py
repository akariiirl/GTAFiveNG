"""Original synthetic flat-grid LOD preview benchmark; no game performance data."""
import argparse
import json
from pathlib import Path
import sys
import time
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from lod import simplify

p=argparse.ArgumentParser(); p.add_argument('--output',type=Path); a=p.parse_args()
v=np.array([[x,y,0.] for x in range(64) for y in range(64)]); f=[]
for x in range(63):
    for y in range(63):
        start=x*64+y; f.extend([[start,start+64,start+1],[start+64,start+65,start+1]])
started=time.perf_counter(); mesh,report=simplify({'v':v,'i':np.array(f),'material':'synthetic'},4)
report.update(seconds=time.perf_counter()-started,workload='Original 64x64 flat-grid vertices',
              limitations='Single offline preview measurement; displacement is vertex-to-cluster distance, not surface error or gameplay suitability.')
print(json.dumps(report,indent=2))
if a.output:
    with a.output.open('x') as stream: json.dump(report,stream,indent=2)
