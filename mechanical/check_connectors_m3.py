"""Check revised connectors against fitted neighbors, case and cable envelopes."""
from pathlib import Path
import cadquery as cq,json,math
D=Path(__file__).resolve().parent/'analog_matrix_package_m3'
g=json.loads((D/'render_geometry.json').read_text()); cache={}; parts={}
for p in g['items']:
    if p['asset'] not in cache:cache[p['asset']]=cq.importers.importStep(str(D/'models'/p['asset'])).val()
    parts[p['ref']]=cache[p['asset']].rotate((0,0,0),(0,0,1),p['rotation']).translate(p['xyz'])
def nearby(a,b):
    a=a.BoundingBox();b=b.BoundingBox()
    return not(a.xmax<b.xmin or a.xmin>b.xmax or a.ymax<b.ymin or a.ymin>b.ymax or a.zmax<b.zmin or a.zmin>b.zmax)
collisions=[]
for i in range(1,10):
    ref='J'+str(i);a=parts[ref]
    for other,b in parts.items():
        if other==ref or not nearby(a,b):continue
        v=a.intersect(b).Volume()
        if v>.001:collisions.append([ref,other,round(v,4)])
case={p.stem:cq.importers.importStep(str(p)).val() for p in (D/'cad').glob('*.step') if p.stem in ['base_tray','signal_cover','power_hood']}
for p in g['items']:
    if p['ref'] not in ['J'+str(i) for i in range(1,9)]:continue
    x,y,z=p['xyz']
    # Conservative coupling-sleeve envelope: OD17, descends 10 mm below mouth.
    env=cq.Solid.makeCylinder(8.5,35,cq.Vector(x,y,z+6.6))
    for name,s in case.items():
        if nearby(env,s):
            v=env.intersect(s).Volume()
            if v>.001:collisions.append([p['ref']+'_plug',name,round(v,4)])
# Three 3 mm OD wire envelopes extend outwards through the right wall.
for y in [27,32.08,37.16]:
    env=cq.Solid.makeCylinder(1.5,20,cq.Vector(159.6,y,16),cq.Vector(1,0,0))
    for name,s in case.items():
        if nearby(env,s):
            v=env.intersect(s).Volume()
            if v>.001:collisions.append(['power_wire',name,round(v,4)])
report={'connector_neighbor_and_cable_intersections':collisions,'bnc_plug_max_diameter_mm':17,
 'bnc_plug_envelope_bottom_z_mm':17.22,'power_wires_max_od_mm':3,'power_wire_direction':'+X',
 'power_screw_access':'Remove independent power hood; screwdriver enters from above',
 'scope':'Nominal CAD; verify actual purchased connector and cable tolerances on first article'}
(D/'connector_access_checks.json').write_text(json.dumps(report,indent=2))
print(report,flush=True);assert not collisions
