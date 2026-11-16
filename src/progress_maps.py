"""Evidence-based, append-only geographic progress maps. No asset extraction.

Areas use rasterized projected triangle unions, not region bounding boxes.
Telemetry is shown as point/path evidence only, never a road-width estimate.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/python-packages'))
import argparse,datetime,hashlib,json,math
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image,ImageDraw
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from validate_surfaces import triangles

COLORS={'verified':'#16a34a','converted':'#248de5','partial':'#e8bf29','failure':'#e14b4b','unknown':'#989fa6'}

def json_read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def mask_triangles(mask,t,lo,res):
    painter=ImageDraw.Draw(mask)
    xy=(t[:,:,:2]-lo)/res
    # Vertical walls have no geographic area.
    cross=(xy[:,1,0]-xy[:,0,0])*(xy[:,2,1]-xy[:,0,1])-(xy[:,1,1]-xy[:,0,1])*(xy[:,2,0]-xy[:,0,0])
    for poly in xy[np.abs(cross)>0.01]: painter.polygon([tuple(v) for v in poly],fill=1)

def generate(build,source,output,checkpoint=None,resolution=2,boundary=None):
    build=Path(build).resolve(); source=Path(source).resolve(); output=Path(output).resolve()
    report=json_read(build/'conversion_report.json'); origin=np.array(report['origin'])
    level=build/'levels/los_santos_fazes'
    objects=[json.loads(l) for l in (level/'main/MissionGroup/Geometry/items.level.json').read_text().splitlines() if l.strip()]
    visual=[o for o in objects if o.get('collisionType')=='None']
    # Bounds from actual DAE position arrays, transformed with the level instances.
    bounds=[]
    for o in visual:
        r=ET.parse(build/o['shapeName'].lstrip('/'))
        arrays=r.findall('.//{*}source')
        vv=[np.fromstring(s.find('{*}float_array').text,sep=' ').reshape(-1,3) for s in arrays if s.get('id','').endswith('-positions')]
        if not vv: continue
        v=np.concatenate(vv)*o['scale']; v=v@np.array(o['rotationMatrix']).reshape(3,3)+o['position']+origin
        bounds.append([v[:,:2].min(axis=0),v[:,:2].max(axis=0)])
    if not bounds: raise ValueError('No converted visual geometry')
    lo=np.floor(np.min(np.array(bounds)[:,0],axis=0)/resolution)*resolution-20
    hi=np.ceil(np.max(np.array(bounds)[:,1],axis=0)/resolution)*resolution+20
    shape=np.ceil((hi-lo)/resolution).astype(int)
    if np.prod(shape)>25000000: raise ValueError('Raster too large; increase --resolution')
    masks={k:Image.new('1',tuple(shape)) for k in ('visual','roads','collision')}
    for o in objects:
        name=Path(o.get('shapeName','')).stem
        if not name: continue
        collision=o.get('collisionType')=='Collision Mesh'
        for t in triangles(build/o['shapeName'].lstrip('/')):
            if not collision: t=(t*np.array(o['scale']))@np.array(o['rotationMatrix']).reshape(3,3)+o['position']
            t=t+origin
            mask_triangles(masks['collision' if collision else 'visual'],t,lo,resolution)
            if not collision and name.startswith('sc1_rd_r'): mask_triangles(masks['roads'],t,lo,resolution)
    m={k:np.array(v,dtype=bool) for k,v in masks.items()}
    grid=np.zeros(m['visual'].shape,dtype=np.uint8)
    grid[m['visual']]=1; grid[m['visual'] & m['collision']]=2
    # Source placement denominator matches converter selection, including exclusions.
    expected=set(); missing_positions=[]
    for p in sorted(source.glob('*.ymap.xml')):
        if any(x in p.name for x in ('oldbill','newbill')): continue
        for e in ET.parse(p).getroot().findall('entities/Item'):
            if e.findtext('lodLevel') not in ('LODTYPES_DEPTH_HD','LODTYPES_DEPTH_ORPHANHD'): continue
            pos=np.array([float(e.find('position').get(k)) for k in 'xyz'])
            if np.linalg.norm(pos[:2]-origin[:2])>report['radius']: continue
            key=(e.findtext('archetypeName'),*pos); expected.add(key)
    converted={(Path(o['shapeName']).stem,*(np.array(o['position'])+origin)) for o in visual}
    # XML coordinates may differ in the last floating digit: compare rounded coordinates.
    def key(k): return (k[0],*(round(float(v),4) for v in k[1:]))
    converted={key(k) for k in converted}; absent=[k for k in expected if key(k) not in converted]
    missing_positions=[k[1:3] for k in absent]
    surfaces=json_read(build/'surface_validation.json') if (build/'surface_validation.json').exists() else None
    failures=[(np.array(s['position'])+origin)[:2] for s in (surfaces or {}).get('failures',[])]
    now=datetime.datetime.now(datetime.timezone.utc); checkpoint=checkpoint or build.name
    digest=hashlib.sha256((build/'conversion_report.json').read_bytes()).hexdigest()
    folder=output/(now.strftime('%Y%m%dT%H%M%S%fZ')+'_'+''.join(c if c.isalnum() or c in '-_' else '_' for c in checkpoint))
    folder.mkdir(parents=True,exist_ok=False)
    summary={'checkpoint':checkpoint,'generated_utc':now.isoformat(),'build_date_utc':datetime.datetime.fromtimestamp((build/'conversion_report.json').stat().st_mtime,datetime.timezone.utc).isoformat(),'build':str(build),'report_sha256':digest,'coordinates':'GTA V original XY metres, Z up','raster_resolution_m':resolution,'raster_bounds_xy':[lo.tolist(),hi.tolist()],
      'exported_projected_area_m2':int(m['visual'].sum())*resolution**2,'exported_road_projected_area_m2':int(m['roads'].sum())*resolution**2,'road_xy_collision_overlap_percent':float((m['roads']&m['collision']).sum()/max(1,m['roads'].sum())*100),
      'asset_completeness':{'expected_instances_in_available_selected_ymaps':len(expected),'converted_matching_instances':len(expected)-len(absent),'percent':100*(len(expected)-len(absent))/len(expected) if expected else None,'missing_placements':len(absent)},
      'missing_texture_names':report.get('missing_textures',[]),'dependency_resolution':report.get('dependency_resolution',{}),
      'whole_island_exported_area_percent':None,'whole_island_verified_drivable_percent':None,'verified_drivable_area_m2':None,'verified_driving_evidence':[],
      'sampled_collision_check':{k:v for k,v in (surfaces or {}).items() if k!='failures'},'documented_collision_failure_points':len(failures),
      'limitations':['Projected raster area is approximate; overlapping floors count once; thin geometry can be overestimated by one pixel.','XY collision overlap ignores height and is not drivable coverage.','No telemetry is attributed automatically to a build; green requires explicit build-matched evidence.','Full-island land boundary unavailable in existing project data. Whole-island area and percentages are null.','Available selected YMAPs are a partial source inventory, not the full island.','Build date is report modification time; source report has no embedded build timestamp.']}
    # Optional authoritative GeoJSON Polygon/MultiPolygon boundary: no invented extents.
    world=None
    if boundary:
        geo=json_read(boundary); geometry=geo.get('geometry',geo)
        polys=geometry['coordinates'] if geometry['type']=='MultiPolygon' else [geometry['coordinates']]
        world=polys; area=0
        for poly in polys:
            for i,ring in enumerate(poly):
                a=np.asarray(ring); area+=(1 if i==0 else -1)*abs(np.dot(a[:,0],np.roll(a[:,1],1))-np.dot(a[:,1],np.roll(a[:,0],1)))/2
        summary['world_boundary']={'path':str(Path(boundary).resolve()),'land_area_m2':area,'note':'Requires GTA XY metre coordinates. No world percent computed without footprint clipping.'}
    def plot(kind,filename):
        fig,ax=plt.subplots(figsize=(14,12)); fig.patch.set_facecolor('#f3f5f7'); ax.set_facecolor(COLORS['unknown'])
        from matplotlib.colors import ListedColormap
        if kind=='heat':
            ax.imshow(grid,origin='lower',extent=[lo[0],hi[0],lo[1],hi[1]],cmap=ListedColormap([COLORS['unknown'],COLORS['partial'],COLORS['converted']]),vmin=0,vmax=2,interpolation='nearest')
        else:
            ax.imshow(np.where(m['visual'],1,0),origin='lower',extent=[lo[0],hi[0],lo[1],hi[1]],cmap=ListedColormap([COLORS['unknown'],COLORS['converted']]),vmin=0,vmax=1,interpolation='nearest')
            road_overlay=np.ma.masked_where(~m['roads'],m['roads'])
            ax.imshow(road_overlay,origin='lower',extent=[lo[0],hi[0],lo[1],hi[1]],cmap=ListedColormap(['#1053a0']),vmin=0,vmax=1,interpolation='nearest',alpha=.7)
        if missing_positions:
            a=np.array(missing_positions); ax.scatter(a[:,0],a[:,1],s=5,c=COLORS['partial'],alpha=.55,label='Missing/unresolved placement')
        if failures:
            a=np.array(failures); ax.scatter(a[:,0],a[:,1],s=45,marker='x',c=COLORS['failure'],linewidth=2)
        if kind=='world':
            if world:
                for poly in world:
                    a=np.array(poly[0]); ax.plot(a[:,0],a[:,1],color='#38424c',lw=1)
                ax.autoscale()
            else:
                ax.text(.5,.98,'FULL ISLAND OUTLINE UNAVAILABLE\nLos Santos / Blaine County geographic context cannot be drawn from current exports.',transform=ax.transAxes,ha='center',va='top',bbox={'facecolor':'white','alpha':.95,'pad':10})
        ax.set_aspect('equal'); ax.set_xlabel('GTA V X (m)'); ax.set_ylabel('GTA V Y (m)'); ax.grid(alpha=.25)
        ax.set_title(f'Project Los Santos | {checkpoint}\n'+{'detail':'Converted neighborhood','world':'World progress — available geographic evidence','heat':'Geometry and collision evidence'}[kind],fontsize=16,pad=18)
        width=ax.get_xlim()[1]-ax.get_xlim()[0]; scale=10**math.floor(math.log10(width/5))
        x=ax.get_xlim()[0]+width*.05; y=ax.get_ylim()[0]+(ax.get_ylim()[1]-ax.get_ylim()[0])*.06
        ax.plot([x,x+scale],[y,y],color='black',lw=4); ax.text(x,y,f'{scale:g} m',va='bottom')
        handles=[Patch(color=COLORS[k],label=label) for k,label in [('verified','Green: build-verified drive evidence (none attributed)'),('converted','Blue: exported geometry / XY collision overlap on heatmap'),('partial','Yellow: unresolved placements / geometry without XY collision'),('failure','Red: documented failed collision sample'),('unknown','Gray: no converted footprint evidenced')]]
        if kind!='heat': handles.append(Patch(color='#1053a0',label='Dark blue: exported road mesh footprint (unverified)'))
        ax.legend(handles=handles,loc='upper left',bbox_to_anchor=(0,-.09),fontsize=9,frameon=False)
        fig.text(.12,.025,f"Build: {summary['build_date_utc'][:19]} UTC | Raster: {resolution:g} m | Exported footprint: {summary['exported_projected_area_m2']/1e6:.3f} km²\nSelected asset completeness: {summary['asset_completeness']['percent']:.1f}% | Island completion: unknown | Verified drivable area: unmeasured",fontsize=10)
        fig.subplots_adjust(bottom=.22,top=.9); fig.savefig(folder/filename,dpi=220); plt.close(fig)
    plot('detail','neighborhood_progress.png'); plot('world','world_progress.png'); plot('heat','conversion_heatmap.png')
    fig,ax=plt.subplots(figsize=(10,8))
    positions=np.array([np.array(o['position'])+origin for o in visual])
    density=ax.hexbin(positions[:,0],positions[:,1],gridsize=30,mincnt=1,cmap='Blues')
    fig.colorbar(density,ax=ax,label='Converted visual placements per bin')
    if missing_positions:
        missing=np.array(missing_positions); ax.scatter(missing[:,0],missing[:,1],marker='x',c='#e8bf29',label='Unresolved placement'); ax.legend()
    ax.set_title('Exported placement density | missing texture names: '+str(len(report.get('missing_textures',[]))))
    ax.set_xlabel('GTA X (m)'); ax.set_ylabel('GTA Y (m)'); ax.set_aspect('equal')
    fig.text(.02,.01,'Available selected inputs only. Texture misses have no inferred geographic footprint. Driving coverage unknown.')
    fig.savefig(folder/'asset_density.png',dpi=120); plt.close(fig)
    (folder/'progress_summary.json').write_text(json.dumps(summary,indent=2))
    # Root files are latest convenience copies; immutable timestamped milestones remain.
    import shutil
    for p in folder.iterdir(): shutil.copyfile(p,output/p.name)
    print(json.dumps({'progress_directory':str(folder),'exported_area_m2':summary['exported_projected_area_m2'],'asset_completeness':summary['asset_completeness']},indent=2))
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('build',type=Path); p.add_argument('--source',type=Path,default=Path('generated/source')); p.add_argument('--output',type=Path,default=Path('generated/progress_maps')); p.add_argument('--checkpoint'); p.add_argument('--resolution',type=float,default=2); p.add_argument('--boundary',type=Path)
    a=p.parse_args()
    if a.resolution<=0: p.error('resolution must be positive')
    generate(a.build,a.source,a.output,a.checkpoint,a.resolution,a.boundary)
