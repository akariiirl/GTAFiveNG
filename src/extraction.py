"""Exact AssetReader task planning from exported metadata and archive inventory.

No guessed DLC order: archive priorities must be supplied. Native decoding needs
an authorized local installation. --execute invokes the existing .NET reader.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
from dependencies import load_policy
from planning import plan
from selection import contains

EXTENSIONS = {'.ymap','.ytyp','.ydr','.ydd','.yft','.ytd','.ybn'}


def normalize(path):
    path=path.replace('\\','/').lower()
    if not path or path.startswith('/') or ':' in path or any(p in ('','..','.') for p in path.split('/')) or Path(path).suffix not in EXTENSIONS:
        raise ValueError('Unsafe or unsupported resource path')
    return path


def export_name(path):
    path=normalize(path)
    return 'resource_'+hashlib.sha256(path.encode()).hexdigest()+'.rpf_'+path.rsplit('/',1)[-1]+'.xml'


def build_tasks(source, inventory, **region):
    source=Path(source); region_plan=plan(source,**region); policy=load_policy(source)
    records=[{**record,'path':normalize(record['path'])} for record in inventory if Path(record['path'].replace('\\','/')).suffix.lower() in EXTENSIONS]
    records.sort(key=lambda record:record['path'])
    index={}
    for record in records: index.setdefault(record['path'].rsplit('/',1)[-1],{})[record['path']]=record
    requests={}; diagnostics=[]; asset_txds={}
    def request(name, extensions, reason):
        candidates={p:r for ext in extensions for p,r in index.get(name.lower()+ext,{}).items()}
        if not candidates:
            diagnostics.append({'name':name,'reason':reason,'status':'missing'}); return
        priorities=policy.get('archive_priorities',{})
        def rank(path):
            return max((value for prefix,value in priorities.items() if path.startswith(prefix.lower().replace('\\','/').rstrip('/')+'/')),default=0)
        best=max(map(rank,candidates)); winners=[p for p in sorted(candidates) if rank(p)==best]
        if len(winners)!=1:
            diagnostics.append({'name':name,'reason':reason,'status':'ambiguous','candidates':winners}); return
        path=winners[0]
        task=requests.setdefault(path,{'path':path,'export':export_name(path),'reasons':[]})
        if reason not in task['reasons']: task['reasons'].append(reason)
    def stem(path, extension): return path.name.split('.rpf_')[-1][:-len(extension)]
    metadata={}
    for path in sorted(source.glob('*.ytyp.xml')):
        for item in ET.parse(path).getroot().findall('.//archetypes/Item'):
            name=item.findtext('name','').lower()
            definition=(item.findtext('assetName',name).lower(),item.findtext('assetType',''),item.findtext('textureDictionary','').lower(),stem(path,'.ytyp.xml'))
            if name: metadata.setdefault(name,set()).add(definition)
    for path in sorted(source.glob('*.ymap.xml')):
        # Seed exported metadata is needed before world-space dependency discovery.
        if any(n in path.name for n in ('oldbill','newbill')): continue
        entities=ET.parse(path).getroot().findall('entities/Item')
        if any(e.findtext('lodLevel') in ('LODTYPES_DEPTH_HD','LODTYPES_DEPTH_ORPHANHD') and contains(region_plan['selection'],[float(e.find('position').get(k,0)) for k in 'xy']) for e in entities):
            request(stem(path,'.ymap.xml'),['.ymap'],'selected YMAP')
    for name, dependency in region_plan['dependencies'].items():
        definitions=metadata.get(name,set())
        if len(definitions)>1:
            diagnostics.append({'name':name,'status':'ambiguous archetype'}); continue
        if definitions:
            asset,kind,txd,ytyp=next(iter(definitions))
            request(ytyp,['.ytyp'],'archetype '+name)
            extensions={ 'ASSET_TYPE_DRAWABLEDICTIONARY':['.ydd'], 'ASSET_TYPE_FRAGMENT':['.yft'], 'ASSET_TYPE_DRAWABLE':['.ydr'] }.get(kind,['.ydr','.ydd','.yft'])
            request(asset,extensions,'visual '+name)
            if txd: asset_txds[name]=txd
            seen=set()
            while txd and txd not in seen:
                seen.add(txd); request(txd,['.ytd'],'texture dictionary '+name)
                txd=policy.get('txd_parents',{}).get(txd,'')
            if txd: diagnostics.append({'name':name,'status':'texture parent cycle'})
        else:
            request(name,['.ydr','.ydd','.yft'],'visual '+name)
    # Bounds must come from inventory evidence; do not infer collision coverage from names.
    from selection import frame
    center,radius,size=frame(region_plan['selection'])
    box=region_plan['selection'].get('bbox',[center[0]-radius,center[1]-radius,center[0]+radius,center[1]+radius])
    for record in records:
        if not record['path'].endswith('.ybn'): continue
        bounds=record.get('bounds_xy')
        if bounds is None:
            diagnostics.append({'path':record['path'],'status':'collision bounds unknown'}); continue
        if len(bounds)!=4 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in bounds) or bounds[0]>bounds[2] or bounds[1]>bounds[3]: raise ValueError('Invalid collision bounds')
        if bounds[2]>=box[0] and bounds[0]<=box[2] and bounds[3]>=box[1] and bounds[1]<=box[3]:
            request(Path(record['path']).stem,['.ybn'],'collision overlap')
    tasks=[{**value,'reasons':sorted(value['reasons'])} for key,value in sorted(requests.items())]
    result={'schema':1,'region_plan_id':region_plan['plan_id'],'tasks':tasks,'diagnostics':diagnostics,
            'texture_policy':{'scoped_textures':True,'asset_txds':asset_txds,'txd_parents':policy.get('txd_parents',{})},
            'inventory_sha256':hashlib.sha256(json.dumps(records,sort_keys=True).encode()).hexdigest(),'in_game_verified':False}
    result['plan_id']=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()
    return result


def execute(task_plan, reader, gta_root, output, plan_path, runner=subprocess.run):
    """Invoke one exact batch; the reader verifies source/output receipts on resume."""
    task_plan_path=Path(plan_path)
    if task_plan_path.exists():
        if json.loads(task_plan_path.read_text())!=task_plan: raise FileExistsError('Preserving different extraction plan')
    else:
        with task_plan_path.open('x') as stream: json.dump(task_plan,stream,indent=2)
    result=runner(['dotnet',str(reader),str(gta_root),str(output),'--tasks',str(task_plan_path)],check=False)
    if result.returncode: raise RuntimeError('AssetReader reported failed/missing tasks; inspect errors.log; outputs preserved')
    exports=[]
    texture_policy={**task_plan.get('texture_policy',{}),'textures':{}}
    texture_policy['txd_parents']=dict(texture_policy.get('txd_parents',{}))
    texture_policy['asset_txds']=dict(texture_policy.get('asset_txds',{}))
    output=Path(output).resolve()
    for task in task_plan['tasks']:
        expected=export_name(task['path'])
        if task['export'] != expected: raise ValueError('Unexpected task output name')
        receipt=json.loads((output/(expected[:-4]+'.receipt.json')).read_text())
        files=receipt.get('Files',{})
        if expected not in files or not receipt.get('Fingerprint'): raise ValueError('Incomplete extraction receipt')
        for name,digest in files.items():
            path=(output/name).resolve()
            if output not in path.parents: raise ValueError('Receipt path escapes output')
            if hashlib.sha256(path.read_bytes()).hexdigest().upper()!=digest: raise ValueError('Extraction receipt mismatch')
        textures={Path(name).stem.lower():name for name in files if name.lower().endswith('.dds')}
        if textures:
            if task['path'].endswith('.ytd'):
                dictionary=Path(task['path']).stem
            else:
                dictionary='embedded_'+hashlib.sha256(task['path'].encode()).hexdigest()
                for reason in dict.fromkeys(task.get('reasons',[])):
                    if not reason.startswith('visual '): continue
                    asset=reason[7:]; parent=task_plan.get('texture_policy',{}).get('asset_txds',{}).get(asset)
                    if parent and parent != dictionary:
                        previous=texture_policy['txd_parents'].get(dictionary)
                        if previous and previous != parent:
                            raise ValueError('Conflicting embedded texture parents: '+dictionary)
                        texture_policy['txd_parents'][dictionary]=parent
                    texture_policy['asset_txds'][asset]=dictionary
            texture_policy['textures'][dictionary]=textures
        exports.append(output/expected)
    policy_path=output/'dependency-policy.json'
    if policy_path.exists():
        if json.loads(policy_path.read_text())!=texture_policy: raise FileExistsError('Preserving different texture policy')
    else:
        with policy_path.open('x') as stream: json.dump(texture_policy,stream,indent=2)
    return exports


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path); parser.add_argument('--inventory',required=True,type=Path)
    parser.add_argument('--plan',required=True,type=Path); parser.add_argument('--center',nargs=2,type=float)
    parser.add_argument('--radius',type=float); parser.add_argument('--bbox',nargs=4,type=float)
    parser.add_argument('--reader',type=Path); parser.add_argument('--gta-root',type=Path); parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    inventory=[json.loads(line) for line in args.inventory.read_text().splitlines() if line.strip()]
    task_plan=build_tasks(args.source,inventory,center=args.center,radius=args.radius,bbox=args.bbox)
    if args.reader:
        if args.gta_root is None or args.output is None: parser.error('--reader requires --gta-root and --output')
        execute(task_plan,args.reader,args.gta_root,args.output,args.plan)
    else:
        with args.plan.open('x') as stream: json.dump(task_plan,stream,indent=2)
