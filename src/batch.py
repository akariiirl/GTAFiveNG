"""Resumable offline region batches with shared conversion cache and resource index.

Each package is an independent level variant; this does not combine them into a
streaming map or make same-level packages safe to install simultaneously.
"""
import argparse
import hashlib
import json
from pathlib import Path
from planning import plan
from region import fingerprints, region_id, run
from selection import selection


def run_batch(source, workspace, regions, maps=True, converter=run):
    source=Path(source).resolve(); workspace=Path(workspace).resolve()
    if workspace==source or source in workspace.parents or workspace in source.parents:
        raise ValueError('Keep source and batch workspace separate')
    configs={region_id(**config):selection(**config) for config in regions}
    if not configs: raise ValueError('At least one region required')
    inputs=fingerprints(source)
    pipeline={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}
    signature={'schema':1,'inputs':inputs,'regions':dict(sorted(configs.items())),'maps':bool(maps),'pipeline':pipeline}
    batch_id=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest()
    folder=workspace/'batches'/batch_id; folder.mkdir(parents=True,exist_ok=True)
    result={'batch_id':batch_id,'signature':signature,'regions':{},'shared_resources':{},'chunks':{},
            'in_game_verified':False,'whole_island_completion_percent':None,
            'limitations':['Independent same-level packages; do not install together.','Shared resources are a build index, not external runtime references.']}
    resources={}
    for key,config in sorted(configs.items()):
        target=converter(source,workspace/'regions',maps=maps,shared_cache=True,**config)
        # package.py emits region.manifest.json alongside region.zip.
        package=json.loads((target/'region.manifest.json').read_text())
        result['regions'][key]={'selection':config,'directory':target.relative_to(workspace).as_posix(),
                                'zip_sha256':package['validation']['zip_sha256']}
        for file in package['files']:
            if '/art/' not in file['path']: continue
            resources.setdefault(file['sha256'],[]).append({'region':key,'path':file['path'],'bytes':file['bytes']})
        region_plan=plan(source,**config)
        for chunk,names in region_plan['chunks'].items():
            record=result['chunks'].setdefault(chunk,{'regions':[],'assets':[]})
            record['regions'].append(key); record['assets']=sorted(set(record['assets'])|set(names))
        # Mutable recovery state is separate from immutable completed milestone.
        state=folder/'state.json'; temporary=folder/'state.json.tmp'
        temporary.write_text(json.dumps({'completed':result['regions']},indent=2)); temporary.replace(state)
    if fingerprints(source)!=inputs: raise ValueError('Source changed during batch; completed regions preserved')
    result['shared_resources']={key:value for key,value in sorted(resources.items()) if len({v['region'] for v in value})>1}
    destination=folder/'batch.json'
    if destination.exists():
        if json.loads(destination.read_text())!=result: raise ValueError('Existing batch manifest changed')
    else:
        with destination.open('x') as stream: json.dump(result,stream,indent=2,sort_keys=True)
    return destination


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path); parser.add_argument('--workspace',required=True,type=Path)
    parser.add_argument('--regions',required=True,type=Path); parser.add_argument('--no-maps',action='store_true')
    args=parser.parse_args()
    print(run_batch(args.source,args.workspace,json.loads(args.regions.read_text()),not args.no_maps))
