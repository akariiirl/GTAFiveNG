"""Small original synthetic DDS cache benchmark; not a BeamNG/FPS benchmark."""
import argparse
import json
from pathlib import Path
import platform
import struct
import sys
import tempfile
import time
import tracemalloc
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from convert import normalized_dds
from resource_cache import ResourceCache, cached_texture, hash_file

parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path); args=parser.parse_args()
with tempfile.TemporaryDirectory() as directory:
    root=Path(directory); header=bytearray(128); header[:4]=b'DDS '
    struct.pack_into('<II',header,12,1024,1024); struct.pack_into('<I',header,80,2); struct.pack_into('<I',header,88,8)
    source=root/'synthetic.dds'; source.write_bytes(header+bytes(range(256))*4096)
    cache=ResourceCache(root/'cache'); measurements={}
    for name in ('cold','warm'):
        tracemalloc.start(); started=time.perf_counter()
        cached_texture(cache,source,root/(name+'.dds'),normalized_dds)
        elapsed=time.perf_counter()-started; _,peak=tracemalloc.get_traced_memory(); tracemalloc.stop()
        measurements[name]={'seconds':elapsed,'python_peak_bytes':peak}
    assert hash_file(root/'cold.dds')==hash_file(root/'warm.dds')
    report={'workload':'original synthetic 1024x1024 alpha-only DDS normalization','input_bytes':source.stat().st_size,
            'output_bytes':(root/'warm.dds').stat().st_size,'measurements':measurements,'outputs_equal':True,
            'platform':platform.platform(),'python':platform.python_version(),
            'limitations':'Single cold/warm observation; tracemalloc measures Python allocations, not RSS or OS cache. No game assets, gameplay or FPS measured.'}
    print(json.dumps(report,indent=2))
    if args.output:
        with args.output.open('x') as stream: json.dump(report,stream,indent=2)
