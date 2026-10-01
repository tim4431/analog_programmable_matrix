"""Parametric prototype housing and populated PCB. Units: mm.

CAD datum: PCB left/rear corner (x=0,y=0), floor underside z=0.
KiCad (x,y) maps to CAD (x,170-y). The verified electrical PCB is read only.
Run with CadQuery 2.8.0. STEP solids are authoritative; renders are illustrations.
"""
from pathlib import Path
import cadquery as cq
import json, shutil, math, hashlib, csv

BASE=Path(__file__).resolve().parent
D=BASE if (BASE/'pcb_geometry.json').exists() else BASE/'analog_matrix_package_m3'
G=json.loads((D/'pcb_geometry.json').read_text())
M=D/'models'; M.mkdir(exist_ok=True)
CAD=D/'cad'; CAD.mkdir(exist_ok=True)
STL=D/'print'; STL.mkdir(exist_ok=True)
PCB_BOTTOM=9.0
PCB_TOP=10.62
FLOOR=3.0
DECK_Z=16.0
LID_T=3.0
TOP_Z=60.0
HOLES=[(4,166),(156,166),(4,44),(156,44),(4,4),(156,20)]
LID_SCREWS=[(-5,175),(165,175),(-5,110),(165,110),(-5,54),(165,54)]
HOOD_SCREWS=[(-5,-7),(165,-7),(-5,43),(165,15)]

def box(x,y,z,dx,dy,dz):
    return cq.Workplane('XY').box(dx,dy,dz,centered=False).translate((x,y,z)).val()
def cyl(x,y,z,r,h):
    return cq.Solid.makeCylinder(r,h,cq.Vector(x,y,z))
def compound(shapes):return cq.Compound.makeCompound(shapes)
def union(shapes):
    result=shapes[0]
    for s in shapes[1:]:result=result.fuse(s)
    return result.clean()
def cut(s,shapes):return s.cut(*shapes).clean() if shapes else s
def bounds(s):
    b=s.BoundingBox();return [round(v,4) for v in (b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax)]
def export(s,path):cq.exporters.export(s,str(path))
def roundbox(x,y,z,dx,dy,dz,r=2):
    w=cq.Workplane('XY').box(dx,dy,dz,centered=False).edges('|Z').fillet(r)
    return w.val().translate((x,y,z))

# Locally authored clearance models: the mechanical envelopes follow the named
# package drawings. Mating threads and internal contacts are simplified.
# Amphenol catalog p118 Fig2: 11 mm body, 16.6 mm above the PCB.
# Clearance model; contact interior and plating are simplified.
bnc=[cyl(0,0,0,5.5,3.9),cyl(0,0,3.9,4.8,12.7),cyl(0,0,-3.81,.45,3.81)]
for x in [-3.45,3.45]:
    for y in [-3.45,3.45]:bnc.append(cyl(x,y,-3.81,1.05,3.81))
for x in [-5.6,5.6]:bnc.append(cq.Solid.makeCylinder(1.0,1.5,cq.Vector(x-.75,0,12.6),cq.Vector(1,0,0)))
bnc=cut(union(bnc),[cyl(0,0,7,3.8,10)])
insulator=cut(cyl(0,0,7,3.65,6.5),[cyl(0,0,7,.75,7)])
socket=cut(cyl(0,0,7,.7,9),[cyl(0,0,13,.35,3.2)])
bnc=compound([bnc,insulator,socket])
export(bnc,M/'BNC_Amphenol_031-5329-52RFX_Vertical.step')

base_soic=cq.importers.importStep(str(M/'SOIC-8_3.9x4.9mm_P1.27mm.step')).val()
for name,epx,epy in [('ADA4899_RD8_EP2.29x2.29',2.29,2.29),
    ('SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.95x4.9mm_Mask2.71x3.4mm',2.71,3.4)]:
    export(compound([base_soic,box(-epx/2,-epy/2,0,epx,epy,.1)]),M/(name+'.step'))

# Pico socket assembly assumes 8.5 mm female housing plus 2.5 mm male spacer.
# Pico PCB underside is 11 mm above the carrier top, not at zero.
pico=[]
for x in [-8.89,8.89]:
    pico.append(box(x-1.27,-25.4,0,2.54,50.8,8.5))
    pico.append(box(x-1.27,-25.4,8.5,2.54,50.8,2.5))
    for n in range(20):pico.append(box(x-.32,-24.13+n*2.54-.32,-3.0,.64,.64,15.5))
module=box(-10.5,-25.5,11,21,51,1)
mounts=[cyl(x,y,10.9,1.05,1.3) for x in [-5.7,5.7] for y in [-23.5,23.5]]
pico.append(cut(module,mounts))
usb=box(-4,21.5,12,8,5.4,3.0)
usb=cut(usb,[box(-3.5,23.5,12.45,7,4,2.1)])
pico.extend([usb,box(-3.5,-3.5,12,7,7,.9),box(-8,15,12,4,3,1.5)])
export(compound(pico),M/'Pico_2x20_Socket_17.78mm.step')

# Installed TO-220 library models include long unsoldered leads. Trim to 2.5 mm
# below the board underside, as specified in the assembly instructions.
to=cq.importers.importStep(str(M/'TO-220-3_Vertical.step')).val()
to=to.intersect(box(-20,-20,-4.12,40,40,40))
export(to,M/'TO-220-3_Vertical_Trimmed.step')

aliases={'BNC_Amphenol_031-5329-52RFX_Vertical':'BNC_Amphenol_031-5329-52RFX_Vertical.step',
 'Pico_2x20_Socket_17.78mm':'Pico_2x20_Socket_17.78mm.step',
 'ADA4899_RD8_EP2.29x2.29':'ADA4899_RD8_EP2.29x2.29.step',
 'TO-220-3_Vertical':'TO-220-3_Vertical_Trimmed.step'}
assets={}; items=[]; placed=[]; model_manifest=[]
for p in G['parts']:
    if p['dnp'] or p['ref'].startswith('H'):continue
    name=aliases.get(p['footprint'],p['models'][0]['file'] if p['models'] else '')
    assert (M/name).is_file(),(p['ref'],name)
    if name not in assets:assets[name]=cq.importers.importStep(str(M/name)).val()
    s=assets[name].rotate((0,0,0),(0,0,1),p['rotation']).translate((p['x'],170-p['y'],PCB_TOP))
    items.append({'ref':p['ref'],'asset':name,'xyz':[p['x'],170-p['y'],PCB_TOP],
        'rotation':p['rotation'],'value':p['value'],'bounds':bounds(s)})
    placed.append((p,s))
    model_manifest.append({'reference':p['ref'],'model':name,'footprint':p['footprint']})
print('Placed components:',len(placed),flush=True)
substrate=cq.importers.importStep(str(D/'pcb_substrate.step')).val()
bb=substrate.BoundingBox(); print('Native board bounds',bounds(substrate),flush=True)
substrate=substrate.translate((0,0,PCB_BOTTOM-bb.zmin))
assert abs(substrate.BoundingBox().zmax-PCB_TOP)<.001

# A shallow tray carries the PCB on six insulating bosses. Cover fasteners sit
# outside the PCB, so they cannot contact traces or require PCB revisions.
outer=roundbox(-10,-12,0,180,192,16,4)
inner=roundbox(-7,-9,3,174,186,14,2)
base=outer.cut(inner)
for x,y in HOLES:base=base.fuse(cyl(x,y,3,4,6))
for x,y in LID_SCREWS+HOOD_SCREWS:base=base.fuse(cyl(x,y,3,4.6,13))
base_cuts=[cyl(x,y,4,2.1,6) for x,y in HOLES]
base_cuts += [cyl(x,y,10.7,2.1,6) for x,y in LID_SCREWS+HOOD_SCREWS]
base_cuts += [cyl(x,-4,-.1,1.7,3.3) for x in [78,156]]
# Intake slots along the rear gap and low side wall. No slot crosses a boss.
for x in range(88,151,7):base_cuts.append(box(x,-7,-.1,4,5,3.3))
for y in [65,80,95,125,140,155]:
    for x in [-10.1,167]:base_cuts.append(box(x,y,5,3.2,10,5))
base_cuts.append(box(166.8,22,12.5,3.5,20,13))
base=cut(base,base_cuts)

lid=roundbox(-10,48,16,180,132,3,3)
# Shallow underside ribs limit flexing of the broad signal cover.
for x in [52,106]:lid=lid.fuse(box(x,60,13.5,2,107,2.5))
for y in [100,140]:lid=lid.fuse(box(25,y,13.5,110,2,2.5))
lidcuts=[cyl(x,170-y,15.8,9,3.5) for x in [7,154] for y in [20,50,80,110]]
for x,y in LID_SCREWS:
    lidcuts.append(cyl(x,y,15.8,1.7,4))
    lidcuts.append(cyl(x,y,17.7,3.1,1.5))
# Vent rows over the high-current output side of the analogue compartment.
for y in [74,104,134,164]:
    for x in [119,124,129,134]:lidcuts.append(box(x,y-6,15.8,2,12,3.5))
lid=cut(lid,lidcuts)

# Rear hood starts 0.3 mm above the tray for assembly clearance; four ears
# overlap onto the tray rim. It is removable independently of the signal lid.
hood=roundbox(-10,-12,16.3,180,59.7,43.7,3)
hood=hood.cut(box(-7,-9,15.9,174,53.7,41.1))
for x,y in HOOD_SCREWS:hood=hood.fuse(cyl(x,y,16,4.4,4))
hoodcuts=[cyl(x,y,15.8,1.7,5) for x,y in HOOD_SCREWS]
hoodcuts += [cyl(x,y,19,3.1,50) for x,y in HOOD_SCREWS]
# Pico cable overmould opening, not merely the metal USB connector outline.
hoodcuts.append(box(-10.1,19,18.5,3.3,20,12))
# Direct access to outward-facing J9; remove hood for top screw access.
hoodcuts.append(box(166.8,22,12.5,3.5,20,13))
for x in range(79,159,5):hoodcuts.append(box(x,-4,56.8,2.5,29,3.5))
for x in range(16,160,6):hoodcuts.append(box(x,-12.1,28,2.5,3.3,25))
for x in range(16,71,6):hoodcuts.append(box(x,44.5,28,2.5,3.5,25))
# Driver access above each mounting ear: hood screws remain reachable vertically.
for x,y in HOOD_SCREWS:hoodcuts.append(cyl(x,y,20,3.5,54))
hood=cut(hood,hoodcuts)

# Heatsink clearance/visualization models, not released thermal parts. The
# mounting plane is 0.30 mm behind the modelled TO-220 tab rear surface.
heatsinks=[]
for cx in [102.46,140.46]:
    sy=170-(153+3.16+.30)
    hs=[box(cx-17.5,sy-1.5,PCB_TOP+.5,35,1.5,38.1)]
    for dx in [-16.5,-11,-5.5,0,5.5,11,16.5]:hs.append(box(cx+dx-.6,sy-13,PCB_TOP+.5,1.2,11.5,38.1))
    heatsinks.append(union(hs))

# A separate insulating G10 bridge restrains the tall sinks. Two 50 mm M3
# aluminium standoffs mount to the tray outside the PCB outline. Soft pads
# contact the fin tops; their final thickness follows the selected sink.
bridge=box(74.2,-7.8,53,85.6,14,3)
bridge=cut(bridge,[cyl(x,-4,52.9,1.7,3.2) for x in [78,156]])
supports=[]
for x in [78,156]:
    post=cq.Workplane('XY').polygon(6,6/math.cos(math.pi/6)).extrude(50).val().translate((x,-4,3))
    post=cut(post,[cyl(x,-4,2.9,1.25,50.2)])
    supports.append(post)
sinktop=PCB_TOP+.5+38.1
pads=[box(x-7,0,sinktop,14,6,53-sinktop) for x in [102.46,140.46]]
export(bridge,CAD/'G10_heatsink_retainer.step')
# 1:1 XY machining profile for 3 mm G10, with two 3.4 mm through holes.
cq.exporters.export(cq.Workplane('XY').add(bridge).faces('>Z').wires(),str(CAD/'G10_heatsink_retainer.dxf'))

case={'base_tray':base,'signal_cover':lid,'power_hood':hood}
for name,s in case.items():
    assert s.isValid(),name
    assert len(s.Solids())==1,(name,'disconnected shell')
    export(s,CAD/(name+'.step'))
    # STL files lie on their best print/finishing reference plane.
    print_s=s
    if name=='signal_cover':print_s=s.rotate((0,0,0),(1,0,0),180)
    elif name=='power_hood':print_s=s.rotate((0,0,0),(1,0,0),180)
    b=print_s.BoundingBox();print_s=print_s.translate((-b.xmin,-b.ymin,-b.zmin))
    cq.exporters.export(print_s,str(STL/(name+'.stl')),tolerance=.08,angularTolerance=.15)
    print('Exported',name,bounds(s),flush=True)

# Common-volume tests catch genuine intersections, including underside leads.
collisions=[]
for cname,shell in case.items():
    sb=shell.BoundingBox()
    for p,part in placed:
        pb=part.BoundingBox()
        if pb.xmax<sb.xmin or pb.xmin>sb.xmax or pb.ymax<sb.ymin or pb.ymin>sb.ymax or pb.zmax<sb.zmin or pb.zmin>sb.zmax:continue
        # An expanded solid AABB is a conservative broad phase. It also avoids
        # OCC common() misclassifying a small part on a remote face extension.
        envelope=box(pb.xmin-.001,pb.ymin-.001,pb.zmin-.001,
            pb.xlen+.002,pb.ylen+.002,pb.zlen+.002)
        if shell.intersect(envelope).Volume()<1e-9:continue
        v=shell.intersect(part).Volume()
        if v>.001:collisions.append({'case':cname,'part':p['ref'],'volume_mm3':round(v,5)})
    v=shell.intersect(substrate).Volume()
    if v>.001:collisions.append({'case':cname,'part':'PCB','volume_mm3':v})
    for n,hs in enumerate(heatsinks):
        v=shell.intersect(hs).Volume()
        if v>.001:collisions.append({'case':cname,'part':'HEATSINK'+str(n),'volume_mm3':v})
for n,hs in enumerate(heatsinks):
    hb=hs.BoundingBox()
    for p,part in placed:
        pb=part.BoundingBox()
        if pb.xmax<hb.xmin or pb.xmin>hb.xmax or pb.ymax<hb.ymin or pb.ymin>hb.ymax:continue
        v=hs.intersect(part).Volume()
        if v>.001:collisions.append({'case':'HEATSINK'+str(n),'part':p['ref'],'volume_mm3':round(v,5)})
for n1,s1 in case.items():
    for n2,s2 in case.items():
        if n1>=n2:continue
        v=s1.intersect(s2).Volume()
        if v>.001:collisions.append({'case':n1,'part':n2,'volume_mm3':round(v,5)})
for name,hardware in [('G10_bridge',bridge)]+[('stand'+str(i),s) for i,s in enumerate(supports)]:
    for cname,s in case.items():
        v=hardware.intersect(s).Volume()
        if v>.001:collisions.append({'case':cname,'part':name,'volume_mm3':round(v,5)})
    for p,s in placed:
        b1=hardware.BoundingBox();b2=s.BoundingBox()
        if b1.xmax<b2.xmin or b1.xmin>b2.xmax or b1.ymax<b2.ymin or b1.ymin>b2.ymax:continue
        v=hardware.intersect(s).Volume()
        if v>.001:collisions.append({'case':name,'part':p['ref'],'volume_mm3':round(v,5)})
print('Case/component collisions',collisions,flush=True)

colors={'base_tray':(.14,.18,.22),'signal_cover':(.81,.83,.82),'power_hood':(.14,.18,.22)}
boardassy=cq.Assembly(name='Analog_matrix_PCB_D')
boardassy.add(substrate,name='PCB',color=cq.Color(.02,.23,.16))
for p,s in placed:
    rgb=(.12,.12,.13) if p['ref'].startswith('U') else (.6,.47,.29)
    if p['ref'].startswith('J'):rgb=(.65,.68,.7) if p['ref']!='J9' else (.04,.4,.2)
    boardassy.add(s,name=p['ref'],color=cq.Color(*rgb))
boardassy.save(str(CAD/'populated_pcb.step'))
assembly=cq.Assembly(name='Analog_matrix_prototype_package')
assembly.add(boardassy,name='PCB_assembly')
for name,s in case.items():assembly.add(s,name=name,color=cq.Color(*colors[name]))
for n,s in enumerate(heatsinks):assembly.add(s,name='Heatsink_ENVELOPE_'+str(n),color=cq.Color(.18,.18,.19))
assembly.add(bridge,name='G10_retaining_bridge',color=cq.Color(.66,.55,.32))
for n,s in enumerate(supports):assembly.add(s,name='M3x50_standoff_'+str(n),color=cq.Color(.65,.68,.7))
for n,s in enumerate(pads):assembly.add(s,name='Silicone_pad_'+str(n),color=cq.Color(.35,.35,.37))
assembly.save(str(CAD/'complete_assembly.step'))

# Tessellated assets feed a render of the same solids, not a separately drawn
# approximation of the case. Preserve one reusable mesh per component type.
def mesh(s):
    vv,ff=s.tessellate(.06,.16)
    return {'vertices':[[v.x,v.y,v.z] for v in vv],'faces':ff}
render_assets={}
for name,s in assets.items():render_assets[name]=[{'mesh':mesh(ss),'bounds':bounds(ss),'volume':ss.Volume()} for ss in s.Solids()]
scene={'assets':render_assets,'items':items,'pcb':mesh(substrate),
       'case':{name:mesh(s) for name,s in case.items()},'heatsinks':[mesh(s) for s in heatsinks],
       'retainer':mesh(bridge),'support_posts':[mesh(s) for s in supports],'sink_pads':[mesh(s) for s in pads],
       'pcb_top':PCB_TOP,'lid_screws':LID_SCREWS,'hood_screws':HOOD_SCREWS,'pcb_holes':HOLES}
(D/'render_geometry.json').write_text(json.dumps(scene,separators=(',',':')))
(D/'model_manifest.json').write_text(json.dumps(model_manifest,indent=2))
report={'pcb_source_sha256':G['source_sha256'],'fitted_components':len(placed),
 'housing_mm':[180,192,60],'nominal_wall_mm':3,'pcb_underside_height_mm':PCB_BOTTOM,
 'native_pcb_thickness_mm':round(PCB_TOP-PCB_BOTTOM,2),'pcb_standoff_height_mm':6,
 'mount_centres_cad_xy_mm':HOLES,'bnc_access_diameter_mm':18,
 'bnc_above_lid_mm':round(PCB_TOP+16.6-19,2),'usb_access_yz_mm':[[19,39],[18.5,30.5]],
 'pico_board_underside_above_carrier_mm':11,'heatsink_roof_gap_mm':round(57-(PCB_TOP+.5+38.1),2),
 'power_entry':{'direction':'+X / right edge','pin1_xy':[155,143],'window_cad_yz_mm':[[22,42],[12.5,25.5]]},
 'heatsink_height_mm':38.1,'solid_intersections':collisions,'case_solid_validity':{k:s.isValid() for k,s in case.items()},
 'retainer_material':'3 mm G10/FR4, unplated; do not print the hot retaining bridge',
 'sink_support_posts_mm':{'centres':[[78,-4],[156,-4]],'length':50,'thread':'M3','max_hex_af':6},
 'limitations':['Heatsinks are reserved envelopes; supplier choice and retainer pad fit remain to be qualified.',
 'No thermal airflow simulation or printed-fit test has been performed.',
 'Generic IC exterior models do not certify exposed-pad land patterns.',
 'Cable plug envelopes assume <=17 mm BNC coupling sleeve OD and <=18x10 mm USB overmould.',
 'Use actual 8.5 mm socket + 2.5 mm header spacer stack. Recheck if substituted.']}
(D/'mechanical_checks.json').write_text(json.dumps(report,indent=2))
assert not collisions,'Resolve geometric intersections before release'
print('CAD package exported; no case/PCB/component intersections.',flush=True)

