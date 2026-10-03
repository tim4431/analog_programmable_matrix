"""Reuse M3 housing geometry and replace the population from the LC1 PCB.

Run in a CadQuery environment after export_metadata.py. Original files are read
only. New package models come from the installed KiCad 8 3D libraries.
"""
from pathlib import Path
import json, os, hashlib
import cadquery as cq
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
D=ROOT/'mechanical';BASE=REPO/'mechanical/analog_matrix_package_m3'
G=json.loads((D/'pcb_geometry.json').read_text())
scene=json.loads((BASE/'render_geometry.json').read_text())
old=json.loads((BASE/'pcb_geometry.json').read_text());oldparts={p['ref']:p for p in old['parts']}
library=Path(os.environ.get('KICAD8_3DMODEL_DIR',r'C:\Program Files\KiCad\8.0\share\kicad\3dmodels'))
def bounds(s):
 b=s.BoundingBox();return [round(v,5) for v in (b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax)]
def mesh(s):
 v,f=s.tessellate(.1,.2);return dict(vertices=[a.toTuple() for a in v],faces=f)
def overlap(a,b):return not any(a[i+1]<b[i] or b[i+1]<a[i] for i in (0,2,4))
def envelope(b):return cq.Workplane('XY').box(b[1]-b[0]+.002,b[3]-b[2]+.002,b[5]-b[4]+.002,centered=False).translate((b[0]-.001,b[2]-.001,b[4]-.001)).val()
assets={};items=[];changed=[];collisions=[]
shells={n:cq.importers.importStep(str(BASE/'cad'/(n+'.step'))).val() for n in scene['case']}
for p in G['parts']:
 if p['dnp']:continue
 m=p['models'][0] if p['models'] else dict(file=p['footprint']+'.step',offset=[0,0,0],rotation=[0,0,0],scale=[1,1,1])
 name=Path(m['file']).with_suffix('.step').name
 if p['footprint'].endswith('_ThermalVias'):name=p['footprint'].removesuffix('_ThermalVias')+'.step'
 if p['footprint']=='TO-220-3_Vertical':name='TO-220-3_Vertical_Trimmed.step'
 path=BASE/'models'/name
 if not path.exists():path=Path(m['file'].replace('${KICAD8_3DMODEL_DIR}',str(library))).with_suffix('.step')
 assert path.is_file(),path
 assert m['offset']==[0,0,0] and m['rotation']==[0,0,0] and m['scale']==[1,1,1],(p['ref'],m)
 if name not in assets:
  assets[name]=cq.importers.importStep(str(path)).val()
  if name not in scene['assets']:scene['assets'][name]=[dict(mesh=mesh(s),bounds=bounds(s),volume=s.Volume()) for s in assets[name].Solids()]
 solid=assets[name].rotate((0,0,0),(0,0,1),p['rotation']).translate((p['x'],170-p['y'],scene['pcb_top']))
 bb=bounds(solid)
 items.append(dict(ref=p['ref'],asset=name,xyz=[p['x'],170-p['y'],scene['pcb_top']],rotation=p['rotation'],value=p['value'],bounds=bb))
 previous=oldparts.get(p['ref'])
 if previous and all(previous[key]==p[key] for key in ['footprint','x','y','rotation']):continue
 changed.append(p['ref'])
 for n,shell in shells.items():
  if not overlap(bb,bounds(shell)):continue
  if shell.intersect(envelope(bb)).Volume()<1e-9:continue
  volume=shell.intersect(solid).Volume()
  if volume>.001:collisions.append(dict(part=p['ref'],case=n,volume_mm3=volume))
 # Heat sinks are unchanged. AABB nonintersection is sufficient for changed
 # low-height parts; report any overlap for exact follow-up, never ignore it.
 for i,sink in enumerate(scene['heatsinks']):
  v=sink['vertices'];sb=[min(a[j] for a in v) for j in range(3)];st=[max(a[j] for a in v) for j in range(3)]
  box=[sb[0],st[0],sb[1],st[1],sb[2],st[2]]
  if overlap(bb,box):collisions.append(dict(part=p['ref'],case='sink'+str(i),needs_exact_review=True))
scene['items']=items
used={p['asset'] for p in items};scene['assets']={key:value for key,value in scene['assets'].items() if key in used}
(D/'render_geometry.json').write_text(json.dumps(scene,separators=(',',':')))
check=dict(pcb_source_sha256=G['source_sha256'],case_revision='M3 unchanged',populated_components=len(items),changed_or_moved_components=len(changed),changed_refs=changed,solid_intersections=collisions,scope='Changed/moved parts checked against original enclosure solids and heatsink bounding envelopes. Unchanged parts retain original M3 checks; no thermal requalification.')
(D/'mechanical_checks.json').write_text(json.dumps(check,indent=2))
assert not collisions,collisions
print('LC1 mechanical check:',len(items),'populated parts;',len(changed),'new/moved; no enclosure or heatsink intersections',flush=True)
