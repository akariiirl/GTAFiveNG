"""Build an original, synthetic-only predictive streaming demo and previews."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from predictive_streaming import plan
from PIL import Image, ImageDraw


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    chunks = {}
    for y in range(12):
        for x in range(100):
            key = f'{x}_{y}'; chunks[key] = {'bounds':[x*128,y*128,(x+1)*128,(y+1)*128],
                'collision_available':True, 'estimated_bytes':250_000 + (x%5)*50_000,
                'dependencies':([f'{x-1}_{y}'] if x and x%10==0 else [])}
    previous = set(); points=[]; loads=0; peak=0; payload=0
    for tick in range(80):
        result = plan(chunks, (tick*128, 4*128), 35, 0, lookahead=3, radius=180, hysteresis=128, previous=previous, load_budget=6)
        previous = set(result['visual_chunks']); loads += len(result['load_now']); peak=max(peak,len(previous))
        payload=max(payload,sum(chunks[k]['estimated_bytes'] for k in previous)); points.append((tick,len(previous),len(result['load_now'])))
    report={'evidence':'SYNTHETIC SIMULATION','synthetic_chunk_count':len(chunks),'ticks':len(points),
        'peak_active_chunks':peak,'load_operations':loads,'estimated_peak_payload_bytes':payload,
        'estimated_only':True,'engine_verified':False,'drivable_chunks':0}
    (args.output/'streaming-summary.json').write_text(json.dumps(report,indent=2)+'\n')
    # Standalone synthetic isometric tiles show distance-band LOD and residency states.
    image=Image.new('RGB',(960,560),'#111827'); draw=ImageDraw.Draw(image)
    colors={'near':'#38bdf8','far':'#475569','loading':'#f97316','collision':'#22c55e','unloaded':'#1f2937'}
    for y in range(8):
        for x in range(12):
            px,py=480+(x-y)*32,80+(x+y)*17
            active=4<=x<=7 and 2<=y<=5; ahead=x==8 and 2<=y<=5
            state='loading' if ahead else ('collision' if active and x<6 else ('near' if active else 'far'))
            dx,dy=24,12
            poly=[(px,py),(px+dx,py-dy),(px+2*dx,py),(px+dx,py+dy)]
            draw.polygon(poly,fill=colors[state],outline='#cbd5e1')
            if state in ('near','loading','collision'):
                draw.polygon([(px,py),(px+dx,py+dy),(px+dx,py+dy+18),(px,py+18)],fill='#0f766e')
    draw.ellipse((458,238,474,254),fill='#facc15',outline='white'); draw.line((466,246,535,246),fill='#facc15',width=4)
    draw.text((20,20),'SYNTHETIC SIMULATION — isometric chunks, near/far LOD, loading, collision-inventory flag; vehicle arrow',fill='white')
    image.save(args.output/'streaming-preview.png')
    svg=['<svg viewBox="0 0 960 360" role="img"><rect width="960" height="360" fill="#111827"/>']
    for tick,active,loads_now in points:
        x=25+tick*12; y=320-active*3
        svg.append(f'<circle cx="{x}" cy="{y}" r="5" fill="#38bdf8"/><circle cx="{x}" cy="{350-loads_now*12}" r="3" fill="#f97316"/>')
    svg.append('</svg>'); plot=''.join(svg)
    page='''<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>Project Los Santos — streaming showcase</title><style>body{font:16px system-ui;background:#0b1220;color:#e5e7eb;margin:auto;max-width:1000px;padding:1rem}section{background:#172033;border-radius:12px;padding:1rem;margin:1rem 0}svg,img{width:100%;height:auto}.tag{color:#fbbf24;font-weight:700}a{color:#7dd3fc}</style><h1>Project Los Santos</h1><p class="tag">SYNTHETIC SIMULATION — previews contain no GTA geometry; no engine loading, verified collision, FPS or RAM measurements.</p><section><h2>Chunk states and near/far LOD</h2><p>Isometric original synthetic tiles: blue near, slate far, orange loading, green collision inventory flag, yellow vehicle/lookahead.</p><img src="streaming-preview.png" alt="Synthetic isometric chunk-state preview"></section><section><h2>Predictive scheduler over 1,200 chunks</h2><p>Blue: active chunks. Orange: load operations per tick.</p>'''+plot+'''<p><a download href="streaming-summary.json">Download summary</a> · <a download href="streaming-preview.png">Download PNG</a> · <a download href="streaming-preview.svg">Download SVG</a></p></section>'''
    (args.output/'streaming-preview.svg').write_text(plot)
    (args.output/'index.html').write_text(page)
    print(json.dumps(report,sort_keys=True))


if __name__ == '__main__': main()
