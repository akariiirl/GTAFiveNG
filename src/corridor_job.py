"""Sequential local corridor build using existing plans, receipts and mesh cache."""
import argparse,datetime,json,os,shutil,subprocess,traceback,uuid
from pathlib import Path
from selected_region import plan
from prepare_selected import prepare
from extraction import execute
from convert import build
from resource_cache import ResourceCache,hash_file
from region import fingerprints
from package import package,validate
from validate_surfaces import validate as surfaces

def save(path,data):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2));tmp.replace(path)

def checked(marker):
    if not marker.exists():return None
    data=json.loads(marker.read_text())
    for name,digest in data['files'].items():
        if hash_file(marker.parent/name)!=digest:raise ValueError('Checkpoint changed: '+name)
    return data

def reuse(tasks,destination,sources):
    destination.mkdir(exist_ok=True);count=0
    for task in tasks['tasks']:
        receipt=task['export'][:-4]+'.receipt.json'
        if (destination/receipt).exists():continue
        for source in sources:
            p=source/receipt
            if not p.exists():continue
            data=json.loads(p.read_text());files=data.get('Files',{})
            if task['export'] not in files:continue
            if not all(source.resolve() in (source/n).resolve().parents and (source/n).is_file() and hash_file(source/n).upper()==h for n,h in files.items()):continue
            for n in files:
                target=destination/n;target.parent.mkdir(parents=True,exist_ok=True)
                if target.exists() and hash_file(target).upper()!=files[n]:raise ValueError('Conflicting recovery file: '+n)
                if not target.exists():shutil.copy2(source/n,target)
            shutil.copy2(p,destination/receipt);count+=1;break
    return count

def run(config_path):
    config=json.loads(config_path.read_text());root=Path(config['root']);workspace=Path(config['workspace'])
    workspace.mkdir(parents=True,exist_ok=True)
    signature={'config':config,'pipeline':{p.name:hash_file(p) for p in Path(__file__).parent.glob('*.py')}}
    signature_path=workspace/'job-inputs.json'
    if signature_path.exists() and json.loads(signature_path.read_text())!=signature:
        raise ValueError('Job inputs changed; use a new workspace and reuse prior extraction receipts')
    if not signature_path.exists():save(signature_path,signature)
    lock=workspace/'job.lock'
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:raise RuntimeError('Job lock exists; verify recorded PID has exited before removing stale lock')
    os.write(fd,str(os.getpid()).encode());os.close(fd)
    state={'pid':os.getpid(),'status':'running','stage':'starting','config':str(config_path.resolve())}
    def progress(stage,**extra):
        if shutil.disk_usage(workspace).free<20*1024**3:raise RuntimeError('Less than 20 GiB free on output volume; safely stopped between stages')
        state.update(stage=stage,updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),**extra)
        save(workspace/'progress.json',state);print(json.dumps(state),flush=True)
    try:
        sources=[Path(s) for s in config['reuse_sources']]
        for stage in config['stages']:
            out=workspace/stage['name'];progress('planning',region=stage['name'])
            if checked(out/'complete.json'):
                sources.insert(0,out/'extracted');continue
            if not (out/'tasks.json').exists():plan(root,out,config['evidence'],stage['bbox'])
            tasks=json.loads((out/'tasks.json').read_text());progress('extraction',task_count=len(tasks['tasks']))
            reused=reuse(tasks,out/'extracted',sources);progress('extraction',receipts_recovered=reused)
            def reader(command,check):
                command[0]=config['dotnet']
                with (out/'extraction.log').open('a') as log:return subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=check)
            execute(tasks,config['reader'],config['gta'],out/'extracted',out/'tasks.json',reader)
            progress('preparing')
            prep=checked(out/'prepared-complete.json')
            if prep:prepared=out/prep['directory']
            else:
                name='prepared-'+str(len(list(out.glob('prepared-*')))).zfill(3)
                prepare(root,out,name);prepared=out/name
                save(out/'prepared-complete.json',{'directory':name,'files':{name+'/'+n:h for n,h in fingerprints(prepared).items()}})
            progress('conversion')
            done=checked(out/'build-complete.json')
            if done:built=out/done['directory']
            else:
                name='build-'+str(len(list(out.glob('build-*')))).zfill(3);built=out/name
                cache=ResourceCache(Path(config.get('mesh_cache',workspace/'mesh-cache')),recover=True)
                if config.get('cache_inputs'):
                    previous=json.loads(Path(config['cache_inputs']).read_text())['pipeline']
                    # Planning and orchestration do not change cached mesh semantics.
                    relevant=('convert.py','primitives.py','lod.py','dependencies.py','resource_cache.py')
                    if any(previous.get(n)!=cache.pipeline.get(n) for n in relevant):
                        raise ValueError('Conversion code changed; previous cache signature cannot be reused')
                    cache.pipeline=previous
                report=build(prepared,built,bbox=stage['bbox'],shared_cache=cache,preselected=True)
                report['source']='GTA V Legacy, explicit CodeWalker dictionary selection; GTA runtime precedence unverified'
                report['selection_mode']='transformed archetype bounds with filtered HD placements'
                save(built/'conversion_report.json',report)
                if not report['visual_instances'] or not report['collision_triangles']:raise ValueError('Empty visual or collision build')
                origin=report['origin'];spawn=[config['spawn'][i]-origin[i] for i in range(3)]
                p=built/'levels/los_santos_fazes/main/MissionGroup/PlayerDropPoints/items.level.json'
                obj=json.loads(p.read_text());obj['position']=spawn;p.write_text(json.dumps(obj)+'\n')
                validate(built)
                save(out/'build-complete.json',{'directory':name,'cache_hits':cache.hits,'cache_misses':cache.misses,'files':{name+'/'+n:h for n,h in fingerprints(built).items()}})
            progress('offline collision validation')
            diagnostic=surfaces(built,1)
            if not diagnostic['sample_count']:raise ValueError('No road collision samples')
            progress('packaging')
            target=out/'neighborhood.zip'
            if target.exists() and not target.with_suffix('.manifest.json').exists():
                if target.resolve().parent!=out.resolve():raise ValueError('Package escaped stage directory')
                target.rename(out/('neighborhood-interrupted-'+uuid.uuid4().hex+'.zip'))
            if not target.exists():package(built,target)
            else:
                manifest=json.loads(target.with_suffix('.manifest.json').read_text())
                if hash_file(target)!=manifest['validation']['zip_sha256']:raise ValueError('Existing package changed')
            # Save the first package before progress plots or a larger stage.
            progress('progress maps',package=str(target))
            from progress_maps import generate
            if not (out/'progress/progress_summary.json').exists():generate(built,prepared,out/'progress',stage['name'],2)
            report=json.loads((built/'conversion_report.json').read_text())
            save(out/'complete.json',{'package':str(target),'build':str(built),'visual_instances':report['visual_instances'],
                'missing_assets':report['missing_assets'],'missing_textures':report['missing_textures'],
                'collision_samples':diagnostic['sample_count'],'collision_failures':len(diagnostic['failures']),
                'in_game_verified':False,'files':{target.name:hash_file(target),target.with_suffix('.manifest.json').name:hash_file(target.with_suffix('.manifest.json'))}})
            sources.insert(0,out/'extracted')
        progress('finished',status='completed')
    except Exception:
        state.update(status='failed',error=traceback.format_exc());save(workspace/'progress.json',state);raise
    finally:lock.unlink()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('config',type=Path);a=p.parse_args();run(a.config)
