"""Nominal M3 BNC insertion and grip review; does not change release geometry."""
from pathlib import Path
import cadquery as cq
import json,math,hashlib,itertools

D=Path(__file__).resolve().parent
M=D.parent/'analog_matrix_package_m3'
g=json.loads((M/'render_geometry.json').read_text())
ports=sorted([p for p in g['items'] if p['asset'].startswith('BNC_')],key=lambda p:int(p['ref'][1:]))
case={name:cq.importers.importStep(str(M/'cad'/(name+'.step'))).val()
      for name in ['base_tray','signal_cover','power_hood']}
def overlap(a,b):
    aa=a.BoundingBox();bb=b.BoundingBox()
    if any([aa.xmax<bb.xmin,bb.xmax<aa.xmin,aa.ymax<bb.ymin,bb.ymax<aa.ymin,aa.zmax<bb.zmin,bb.zmax<aa.zmin]):return 0.
    return max(0.,a.intersect(b).Volume())
def cylinder(x,y,z,r,h):return cq.Solid.makeCylinder(r,h,cq.Vector(x,y,z))
results=[];envelopes={};collisions=[]
for p in ports:
    x,y,z=p['xyz'];mouth=z+16.6
    # 17 mm OD at every angle; axial sweep from conservative locked position
    # through the full vertical withdrawal path. Mating jack itself excluded.
    env=cylinder(x,y,mouth-10,8.5,100)
    envelopes[p['ref']]=env
    for name,s in case.items():
        v=overlap(env,s)
        if v>.001:collisions.append([p['ref'],name,round(v,5)])
    radius=7.25  # 14.5 mm collar, Amphenol catalog p108, 31-320-RFX
    results.append({'reference':p['ref'],'label':('a' if x<80 else 'b')+str(round((150-y)/30)),
      'cad_xy_mm':[x,y],'mouth_above_cover_mm':round(mouth-19,3),
      'nominal_14_5mm_collar_radial_hole_gap_mm':9-radius,
      'checked_17mm_collar_radial_hole_gap_mm':.5,
      'nominal_14_5mm_collar_to_hood_plane_mm':round(y-47.7-radius,3),
      'checked_17mm_collar_to_hood_plane_mm':round(y-47.7-8.5,3),
      'insertion_envelope_min_clearance_mm':min(.5,round(y-47.7-8.5,3))})
print('Eight insertion paths checked.',flush=True)
for (ra,a),(rb,b) in itertools.combinations(envelopes.items(),2):
    if overlap(a,b)>.001:collisions.append([ra,rb,'plug_to_plug'])

# Human-factors screening only: two 10 mm diameter, 20 mm tall fingertip
# cylinders around the collar; fingers hover above the lid (z=20..40).
# Touch geometry is illustrative, not an anthropometric or usability proof.
grip_results=[]
for p in ports:
    x,y,z=p['xyz'];all_hits={};clearance={}
    for name,angles in [('two_45deg_turns_with_regrip',range(-22,23,2)),('single_90deg_turn',range(-45,46,3))]:
        # Include the exact +/-22.5-degree endpoints in the first case.
        angles=list(angles)+([-22.5,22.5] if name.startswith('two_') else [])
        hits=set();minimum=1e9
        for angle in angles:
            theta=math.radians(angle)
            for sign in [-1,1]:
                finger=cylinder(x+sign*14*math.cos(theta),y+sign*14*math.sin(theta),20,5,20)
                # AABB separation is a conservative lower bound on distance.
                # Avoid repeated exact distance solves on hundreds of hood faces.
                for target,s in list(case.items())+[(r,s) for r,s in envelopes.items() if r!=p['ref']]:
                    fa=finger.BoundingBox();sa=s.BoundingBox()
                    lower_bound=math.sqrt(sum(v*v for v in [max(0,fa.xmin-sa.xmax,sa.xmin-fa.xmax),max(0,fa.ymin-sa.ymax,sa.ymin-fa.ymax),max(0,fa.zmin-sa.zmax,sa.zmin-fa.zmax)]))
                    minimum=min(minimum,lower_bound)
                    if overlap(finger,s)>.001:hits.add(target)
        all_hits[name]=sorted(hits);clearance[name]=round(minimum,4)
    grip_results.append({'reference':p['ref'],'collisions':all_hits,'minimum_clearance_lower_bound_mm':clearance})
    print('Grip screen checked:',p['ref'],flush=True)

report={'enclosure':'M3','pcb':'D','geometry_sha256':hashlib.sha256((M/'render_geometry.json').read_bytes()).hexdigest(),
 'nominal_reference_plug':'Amphenol 31-320-RFX; catalog diameter 14.5 mm, total length 29.8 mm',
 'reference_source':'https://www.farnell.com/datasheets/1942962.pdf (Amphenol catalog p108)',
 'checked_plug_envelope':{'maximum_diameter_mm':17,'below_jack_mouth_mm':10,'vertical_sweep_height_mm':100,
 'scope':'Straight rotationally symmetric envelope; mating depth assumed conservatively, not a vendor mated STEP assembly.'},
 'port_pitch_mm':30,'aperture_diameter_mm':18,'plug_to_plug_gap_14_5mm_mm':15.5,'plug_to_plug_gap_17mm_mm':13,
 'collisions':collisions,'ports':results,'finger_screen':grip_results,
 'conclusion':'Straight BNC plugs within the checked envelope clear. a3/b3 rear access is restricted; grip from the sides and regrip if needed.',
 'limitations':['Nominal geometry, no printed prototype or hand trial.',
 '17 mm collar leaves only 0.5 mm radial hole margin before manufacturing and alignment tolerances.',
 'The illustrative fingertip model is not a general ergonomic certification.',
 'Right-angle plugs, BNC tees and oversized boots are not covered.',
 'Route cable upward or outward; cable minimum bend radius must follow the selected cable data.']}
(D/'bnc_access_checks.json').write_text(json.dumps(report,indent=2))
assert not collisions,collisions
assert all(not r['collisions']['two_45deg_turns_with_regrip'] for r in grip_results)
print(json.dumps({'plug_collisions':collisions,'tight_ports':[r for r in results if r['label'] in ['a3','b3']],
 'single_90deg_grip_obstructions':[r['reference'] for r in grip_results if r['collisions']['single_90deg_turn']]},indent=2),flush=True)
