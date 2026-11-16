"""Local-only inventory-to-package controller. Dry-run never probes game files."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import re
import xml.etree.ElementTree as ET
from selection import selection, contains

ROOT=Path(__file__).resolve().parents[1]

def safe_metadata(data):
    def replace(match):
        value=match.group(1).lower()
        code=int(value[1:],16) if value.startswith(b'x') else int(value)
        return b'' if code<32 and code not in (9,10,13) else match.group(0)
    return re.sub(rb'&#(x[0-9a-fA-F]+|[0-9]+);',replace,data)


def plan_execution(regions, workspace, gta_root=None):
    selections=[selection(**config) for config in regions]
    if not selections: raise ValueError('At least one region required')
    return {'schema':1,'dry_run':True,'workspace':str(workspace),'gta_root':str(gta_root) if gta_root else 'GTA_ROOT required for execution',
            'regions':selections,'stages':['dependencies','native bootstrap','active metadata view','exact extraction','region conversion','single-level composition','collision diagnostics','progress maps','isolated handoff'],
            'game_files_accessed':False,'in_game_verified':False}


def active_metadata(snapshot, policy, destination, regions=None):
    records=[json.loads(line) for line in (snapshot/'inventory.jsonl').read_text().splitlines() if line.strip()]
    groups={}
    for record in records:
        if record.get('xml'): groups.setdefault(record['name'],[]).append(record)
    relevant=set(groups)
    if regions is not None:
        from dependencies import joaat
        relevant=set(); required=set()
        def xml(record):
            data=(snapshot/record['xml']).read_bytes()
            if hashlib.sha256(data).hexdigest()!=record['xml_sha256']: raise ValueError('Catalog metadata hash mismatch: '+record['path'])
            try: return ET.fromstring(safe_metadata(data))
            except ET.ParseError as ex: raise ValueError('Invalid metadata XML: '+record['path']+': '+str(ex)) from ex
        for name,candidates in groups.items():
            if not name.endswith('.ymap'): continue
            for record in candidates:
                for item in xml(record).findall('entities/Item'):
                    if item.findtext('lodLevel') not in ('LODTYPES_DEPTH_HD','LODTYPES_DEPTH_ORPHANHD'): continue
                    pos=item.find('position')
                    if pos is None: raise ValueError('YMAP entity has no position: '+record['path'])
                    xy=[float(pos.get(k)) for k in ('x','y')]
                    if any(contains(region,xy) for region in regions):
                        relevant.add(name); required.add(item.findtext('archetypeName','').strip().lower())
        required_hashes={int(m.group(1),16) for n in required if (m:=re.fullmatch(r'hash_([0-9a-f]{8})',n))}
        for name,candidates in groups.items():
            if not name.endswith('.ytyp'): continue
            for record in candidates:
                for item in xml(record).findall('.//archetypes/Item'):
                    archetype=item.findtext('name','').strip().lower()
                    try: hashed=joaat(archetype) if archetype else None
                    except UnicodeEncodeError: hashed=None
                    if archetype in required or hashed in required_hashes:
                        relevant.add(name); break
    selected=[]; unrelated=[]; ambiguous=[]
    for name,candidates in sorted(groups.items()):
        def rank(record):
            return max((value for prefix,value in policy.get('archive_priorities',{}).items() if record['path'].startswith(prefix.lower().replace('\\','/').rstrip('/')+'/')),default=0)
        best=max(map(rank,candidates)); winners=[r for r in candidates if rank(r)==best]
        if name not in relevant:
            if len(winners)>1 and len({r['xml_sha256'] for r in winners})>1: unrelated.append(name)
            continue
        if len(winners)>1 and len({r['xml_sha256'] for r in winners})>1:
            ambiguous.append({'name':name,'candidates':[r['path'] for r in winners]}); continue
        selected.append(sorted(winners,key=lambda r:r['path'])[0])
    destination.mkdir(parents=True,exist_ok=True)
    report=destination/'metadata-conflicts.json'; contents=json.dumps({'relevant':ambiguous,'unrelated':unrelated},indent=2)
    if report.exists():
        if report.read_text()!=contents: raise ValueError('Changed metadata conflict report preserved')
    else: report.write_text(contents)
    if ambiguous: raise ValueError('Ambiguous relevant metadata requires archive policy: '+str(len(ambiguous)))
    for record in selected:
        source=snapshot/record['xml']; target=destination/record['xml']
        raw=source.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=record['xml_sha256']: raise ValueError('Catalog metadata hash mismatch: '+record['path'])
        data=safe_metadata(raw)
        if target.exists():
            if target.read_bytes()!=data: raise ValueError('Changed metadata view preserved')
        else: target.write_bytes(data)
    path=destination/'dependency-policy.json'
    if path.exists() and json.loads(path.read_text())!=policy: raise ValueError('Changed metadata policy preserved')
    if not path.exists(): path.write_text(json.dumps(policy,sort_keys=True,indent=2))
    return records


def run_workflow(regions, workspace, gta_root, reader=None, policy=None, allow_missing=False, native_runner=None, reuse_catalog=False):
    from batch import run_batch
    from compose import compose
    from extraction import build_tasks, execute
    from progress_maps import generate
    from region import run
    from resource_cache import hash_file
    from validate_surfaces import validate as surfaces
    selections=plan_execution(regions,workspace,gta_root)['regions']
    workspace=Path(workspace).resolve(); gta_root=Path(gta_root).resolve(); reader=Path(reader or ROOT/'src/AssetReader/bin/Release/net8.0/AssetReader.dll').resolve()
    if workspace==gta_root or gta_root in workspace.parents or workspace in gta_root.parents: raise ValueError('Workspace must be separate from game files')
    if not (gta_root/'GTA5.exe').is_file(): raise ValueError('GTA V Legacy root must contain GTA5.exe')
    for package in ('numpy','PIL','matplotlib'):
        if importlib.util.find_spec(package) is None: raise RuntimeError('Install requirements-cloud.txt; missing '+package)
    runner=native_runner or subprocess.run
    workspace.mkdir(parents=True,exist_ok=True)
    state={'stage':'dependencies','completed':[],'in_game_verified':False}
    def checkpoint(stage):
        if stage!=state['stage'] and state['stage'] not in state['completed']: state['completed'].append(state['stage'])
        state['stage']=stage
        temporary=workspace/'workflow-state.json.tmp'; temporary.write_text(json.dumps(state,indent=2)); temporary.replace(workspace/'workflow-state.json')
    def command(args):
        result=runner(args,check=False)
        if result.returncode: raise RuntimeError('Native command failed: '+str(args))
    try:
        if not reader.exists():
            command(['dotnet','build',str(ROOT/'src/AssetReader/AssetReader.csproj'),'-c','Release'])
        if not reader.exists(): raise RuntimeError('AssetReader DLL missing after build')
        checkpoint('native bootstrap')
        catalog=workspace/'catalog'
        if not reuse_catalog: command(['dotnet',str(reader),str(gta_root),str(catalog),'--bootstrap'])
        bootstrap=json.loads((catalog/'bootstrap.json').read_text())
        if bootstrap['errors']: raise RuntimeError('Native inventory has errors; inspect snapshot index-errors.jsonl')
        snapshot=Path(bootstrap['snapshot']).resolve()
        if not snapshot.is_dir(): raise ValueError('Bootstrap snapshot missing')
        if reuse_catalog:
            stamp=(catalog/'bootstrap.json').stat().st_mtime_ns
            inventory_path=snapshot/'inventory.jsonl'
            if not inventory_path.is_file(): raise ValueError('Completed inventory missing')
            archives=list(gta_root.rglob('*.rpf'))
            present={p.relative_to(gta_root).as_posix().lower() for p in archives}
            with inventory_path.open(encoding='utf-8') as stream:
                indexed={json.loads(line).get('archive') for line in stream if line.strip()}
            indexed.discard(None)
            if (reader.stat().st_mtime_ns>stamp or inventory_path.stat().st_mtime_ns>stamp
                or any(p.stat().st_mtime_ns>stamp for p in archives) or not indexed.issubset(present)):
                raise ValueError('Reader or archive changed since bootstrap; run native bootstrap again')
        policy=policy or {}
        signature={'snapshot':str(snapshot),'regions':selections,'policy':policy,'allow_missing':allow_missing,
                   'pipeline':{p.name:hash_file(p) for p in Path(__file__).parent.glob('*.py')}}
        run_id=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest(); run_root=workspace/'runs'/run_id; run_root.mkdir(parents=True,exist_ok=True)
        completion=run_root/'completion.json'
        if completion.exists():
            result=json.loads(completion.read_text())
            for relative,digest in result['artifacts'].items():
                path=(run_root/relative).resolve()
                if run_root not in path.parents or hash_file(path)!=digest: raise ValueError('Completed workflow artifact changed; preserved')
            checkpoint('complete'); return run_root/'handoff/handoff.json'
        checkpoint('active metadata view')
        source=run_root/'metadata'; inventory=active_metadata(snapshot,policy,source,selections)
        checkpoint('exact extraction')
        plans=[build_tasks(source,inventory,**config) for config in selections]; tasks={}; diagnostics=[]; texture_policy={'scoped_textures':True,'asset_txds':{},'txd_parents':policy.get('txd_parents',{})}
        for plan in plans:
            diagnostics.extend(plan['diagnostics']); texture_policy['asset_txds'].update(plan['texture_policy']['asset_txds'])
            for task in plan['tasks']:
                current=tasks.setdefault(task['path'],{**task,'reasons':[]}); current['reasons']=sorted(set(current['reasons'])|set(task['reasons']))
        (run_root/'dependency-diagnostics.json').write_text(json.dumps(diagnostics,indent=2))
        if diagnostics and not allow_missing: raise ValueError('Unresolved/unknown dependencies; inspect dependency-diagnostics.json or explicitly allow incomplete output')
        task_plan={'schema':1,'tasks':[tasks[k] for k in sorted(tasks)],'texture_policy':texture_policy}
        # Recover verified completed tasks into a fresh extraction attempt; preserve partial artifacts.
        attempts=sorted(run_root.glob('extraction-*'))
        extracted=run_root/('extraction-'+str(len(attempts)).zfill(4)); extracted.mkdir()
        for attempt in attempts:
            for receipt_path in attempt.glob('*.receipt.json'):
                receipt=json.loads(receipt_path.read_text()); files=receipt.get('Files',{})
                if not files: continue
                valid=True
                for name,digest in files.items():
                    path=(attempt/name).resolve()
                    if attempt.resolve() not in path.parents or not path.is_file() or hash_file(path).upper()!=digest: valid=False; break
                if not valid: continue
                for name in files:
                    target=extracted/name; target.parent.mkdir(parents=True,exist_ok=True)
                    if not target.exists(): shutil.copyfile(attempt/name,target)
                if not (extracted/receipt_path.name).exists(): shutil.copyfile(receipt_path,extracted/receipt_path.name)
        execute(task_plan,reader,gta_root,extracted,run_root/'tasks.json',runner)
        checkpoint('region conversion')
        def recover_region(source,workspace,**kwargs):
            kwargs['repair_cache']=True
            for attempt in range(100):
                target=workspace if attempt==0 else workspace/('recovery-'+str(attempt))
                try: return run(source,target,**kwargs)
                except FileExistsError: continue
            raise RuntimeError('Too many preserved partial region attempts')
        batch_path=run_batch(extracted,run_root/'batch',selections,converter=recover_region)
        batch=json.loads(batch_path.read_text()); builds=[run_root/'batch'/record['directory']/'build' for record in batch['regions'].values()]
        checkpoint('single-level composition')
        composed=None
        for attempt in range(100):
            candidate=run_root/('composed' if attempt==0 else 'composed-'+str(attempt))
            try: composed=compose(builds,candidate); break
            except FileExistsError: continue
        if composed is None: raise RuntimeError('Too many partial compositions')
        checkpoint('collision diagnostics'); collision=surfaces(composed)
        checkpoint('progress maps'); generate(composed,extracted,run_root/'progress','composed-local-handoff')
        checkpoint('isolated handoff')
        handoff=run_root/'handoff'; handoff.mkdir(exist_ok=True); profile=handoff/'isolated-profile'; mods=profile/'current/mods'; mods.mkdir(parents=True,exist_ok=True)
        target=mods/'los_santos_fazes.zip'; source_zip=composed/'composed.zip'; package_hash=hash_file(source_zip)
        if target.exists() and hash_file(target)!=package_hash: raise ValueError('Isolated profile package changed; preserved')
        if not target.exists(): shutil.copyfile(source_zip,target)
        result={'package':str(source_zip),'package_sha256':package_hash,'profile':str(profile),'profile_package':str(target),
                'collision_diagnostics':collision,'dependency_diagnostics':diagnostics,'in_game_verified':False,
                'instructions':'Launch only with this isolated userpath. Inspect visuals/collision before driving. No automatic vehicle control.'}
        (handoff/'handoff.json').write_text(json.dumps(result,indent=2))
        shutil.copyfile(ROOT/'tools/launch_handoff.ps1',handoff/'launch.ps1')
        artifacts=[source_zip,composed/'composed.manifest.json',target,handoff/'handoff.json',handoff/'launch.ps1',run_root/'progress/progress_summary.json']
        completion.write_text(json.dumps({'artifacts':{p.relative_to(run_root).as_posix():hash_file(p) for p in artifacts}},indent=2))
        checkpoint('complete'); return handoff/'handoff.json'
    except Exception as ex:
        state['error']=str(ex); checkpoint(state['stage'])
        (workspace/('error-'+uuid.uuid4().hex+'.json')).write_text(json.dumps(state,indent=2))
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--regions',required=True,type=Path); p.add_argument('--workspace',required=True,type=Path)
    p.add_argument('--gta-root',default=os.environ.get('GTA_ROOT')); p.add_argument('--reader',type=Path); p.add_argument('--policy',type=Path)
    p.add_argument('--dry-run',action='store_true'); p.add_argument('--allow-missing',action='store_true'); p.add_argument('--reuse-catalog',action='store_true'); a=p.parse_args()
    regions=json.loads(a.regions.read_text())
    if a.dry_run: print(json.dumps(plan_execution(regions,a.workspace,a.gta_root),indent=2))
    else:
        if not a.gta_root: p.error('Supply --gta-root or GTA_ROOT environment variable')
        print(run_workflow(regions,a.workspace,a.gta_root,a.reader,json.loads(a.policy.read_text()) if a.policy else None,a.allow_missing,reuse_catalog=a.reuse_catalog))
