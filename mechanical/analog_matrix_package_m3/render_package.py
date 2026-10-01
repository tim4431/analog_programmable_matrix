"""Blender 4.3 rendering from tessellated CAD, with actual PCB artwork."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector
BASE=Path(__file__).resolve().parent
D=BASE if (BASE/'render_geometry.json').exists() else BASE/'analog_matrix_package_m3'
R=D/'renders';R.mkdir(exist_ok=True)
data=json.loads((D/'render_geometry.json').read_text())
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.001
scene.render.engine='CYCLES';scene.cycles.samples=48
scene.cycles.use_denoising=True
scene.render.resolution_x=1800;scene.render.resolution_y=1600;scene.render.resolution_percentage=100
scene.world.color=(.22,.22,.22)
scene.view_settings.view_transform='AgX'

def mat(name,rgb,metal=0,rough=.45):
    m=bpy.data.materials.new(name);m.use_nodes=True
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(*rgb,1)
    p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
    return m
materials={
 'body':mat('Graphite IC',(.06,.068,.078)),
 'silver':mat('Solder and leads',(.62,.66,.69),.8,.27),
 'gold':mat('Gold connector',(.7,.47,.12),.8,.23),
 'ceramic':mat('Ceramic',(.52,.32,.16)),
 'resistor':mat('Thin film resistor',(.12,.14,.15)),
 'pcb':mat('Green FR4',(.025,.21,.115),0,.42),
 'tantalum':mat('Tantalum body',(.48,.3,.14)),
 'terminal':mat('Terminal green',(.04,.34,.19)),
 'navy':mat('Charcoal PA12',(.045,.075,.10),0,.54),
 'lid':mat('Warm gray PA12',(.70,.73,.71),0,.48),
 'sink':mat('Black anodized aluminum',(.07,.075,.08),.65,.37),
 'ink':mat('Blue panel ink',(.012,.04,.065)),
 'white':mat('White markings',(.85,.89,.89)),
 'rubber':mat('Elastomer feet',(.025,.026,.028)),
 'ground':mat('Studio',(.73,.76,.78))}

def objmesh(name,g,material):
    m=bpy.data.meshes.new(name);m.from_pydata(g['vertices'],[],g['faces']);m.update()
    o=bpy.data.objects.new(name,m);scene.collection.objects.link(o);o.data.materials.append(material)
    return o
def bevel(o,w=.2):
    mod=o.modifiers.new('Edge highlights','BEVEL');mod.width=w;mod.segments=2
    o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
def cube(name,loc,size,material):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(material);bevel(o,.2)
    return o
def text(label,loc,size,material=materials['ink'],rotation=(0,0,math.pi)):
    c=bpy.data.curves.new(label,'FONT');c.body=label;c.align_x='CENTER';c.size=size;c.extrude=.002
    o=bpy.data.objects.new(label,c);scene.collection.objects.link(o);o.location=loc;o.rotation_euler=rotation;o.data.materials.append(material)
    return o
pcb_objects=[]
o=objmesh('Drilled PCB',data['pcb'],materials['pcb']);pcb_objects.append(o)
# Surface artwork follows the existing verified PCB export. Native hole solids
# remain underneath; no schematic elements or invented routing are introduced.
im=bpy.data.images.load(str(D/'pcb_surface.png'));im.pack()
texture=mat('Actual PCB artwork',(1,1,1),0,.48)
n=texture.node_tree.nodes.new('ShaderNodeTexImage');n.image=im
texture.node_tree.links.new(n.outputs['Color'],next(p for p in texture.node_tree.nodes if p.type=='BSDF_PRINCIPLED').inputs['Base Color'])
topmesh={'vertices':[(0,0,data['pcb_top']+.005),(160,0,data['pcb_top']+.005),(160,170,data['pcb_top']+.005),(0,170,data['pcb_top']+.005)],'faces':[(0,1,2,3)]}
o=objmesh('PCB surface artwork',topmesh,texture)
uv=o.data.uv_layers.new(name='UVMap')
for lp,xy in zip(o.data.loops,[(0,0),(1,0),(1,1),(0,1)]):uv.data[lp.index].uv=xy
pcb_objects.append(o)
asset_meshes={}
for name,solids in data['assets'].items():
    arr=[];maxvol=max(s['volume'] for s in solids)
    for i,s in enumerate(solids):
        b=s['bounds'];m=materials['silver'];v=s['volume']
        if 'BNC_' in name:
            m=materials['silver']
            if 7.1 < b[1]-b[0] < 7.4:m=materials['white']
            if b[1]-b[0]<1.5:m=materials['gold']
        elif 'Pico_' in name:
            if b[2]<-25 and b[4]>10:m=materials['pcb']
            elif b[4]>=0 and b[5]>=8 and (b[1]-b[0])>2:m=materials['body']
            if b[2]>20 and b[4]>=11.9:m=materials['silver']
        elif v>maxvol*.60:
            if name.startswith('R_'):m=materials['resistor']
            elif name.startswith('C_') and 'Radial' not in name:m=materials['ceramic']
            elif name.startswith('CP_'):m=materials['tantalum']
            elif name.startswith('Terminal'):m=materials['terminal']
            else:m=materials['body']
        mesh=bpy.data.meshes.new(name+str(i));mesh.from_pydata(s['mesh']['vertices'],[],s['mesh']['faces']);mesh.update();mesh.materials.append(m);arr.append(mesh)
    asset_meshes[name]=arr
for p in data['items']:
    for j,mesh in enumerate(asset_meshes[p['asset']]):
        o=bpy.data.objects.new(p['ref']+'_'+str(j),mesh);scene.collection.objects.link(o)
        o.location=p['xyz'];o.rotation_euler[2]=math.radians(p['rotation']);pcb_objects.append(o)

case={}
for name,g in data['case'].items():
    o=objmesh(name,g,materials['lid'] if name=='signal_cover' else materials['navy']);bevel(o,.22);case[name]=o
sinks=[objmesh('Heatsink envelope '+str(i),g,materials['sink']) for i,g in enumerate(data['heatsinks'])]
for o in sinks:bevel(o,.1)
retainers=[objmesh('G10 heat sink retaining bridge',data['retainer'],materials['ceramic'])]
retainers += [objmesh('50 mm M3 standoff',g,materials['silver']) for g in data['support_posts']]
retainers += [objmesh('Silicone restraint',g,materials['rubber']) for g in data['sink_pads']]
feet=[cube('Adhesive foot',(x,y,-1.25),(12,12,2.5),materials['rubber']) for x,y in [(2,2),(158,2),(2,168),(158,168)]]
lidlabels=[]
lidlabels.append(text('ANALOG MATRIX',(80,155,19.04),6.2))
lidlabels.append(text('4 x 4   /   DC - 1 MHz',(80,165,19.04),3.1))
for i,y in enumerate([20,50,80,110]):
    lidlabels.append(text('a'+str(i),(24,170-y+1,19.04),4.2))
    lidlabels.append(text('b'+str(i),(135,170-y+1,19.04),4.2))
lidlabels.append(text('INPUT  +/-1 V',(39,53,19.04),2.8))
lidlabels.append(text('OUTPUT  50 ohm',(121,53,19.04),2.8))
lidlabels.append(text('b = M a',(80,101,19.04),6.5))
lidlabels.append(text('STATIC COEFFICIENTS  -1 TO +1',(80,112,19.04),2.3))
hoodlabels=[text('POWER / CONTROL',(53,19,60.04),3.9,materials['white']),
            text('+/-15 V     USB',(53,30,60.04),2.8,materials['white'])]
for y,label in [(27,'+15'),(32.08,'GND'),(37.16,'-15')]:
    hoodlabels.append(text(label,(170.035,y,27),1.35,materials['white'],(math.pi/2,0,math.pi/2)))
for labels,name in [(lidlabels,'signal_cover'),(hoodlabels,'power_hood')]:
    for o in labels:o.parent=case[name]

def screw(x,y,z):
    bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=2.8,depth=1.15,location=(x,y,z));o=bpy.context.object;o.name='M3 fastener';o.data.materials.append(materials['silver']);bevel(o,.12)
    return o
fasteners=[screw(x,y,18.35) for x,y in data['lid_screws']]
for o in fasteners:o.parent=case['signal_cover']
for x,y in data['hood_screws']:
    o=screw(x,y,19.6);o.parent=case['power_hood']
fasteners_board=[screw(x,y,11.7) for x,y in data['pcb_holes']]

cube('Studio floor',(90,105,-4.5),(2000,2000,2),materials['ground'])
def light(name,loc,power,size):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((90,105,25))-o.location).to_track_quat('-Z','Y').to_euler()
light('Key',(-170,350,490),4500000,350)
light('Fill',(400,40,330),2200000,280)
light('Rim',(20,-260,350),3000000,230)
bpy.ops.object.camera_add();cam=bpy.context.object;scene.camera=cam;cam.data.type='ORTHO'
def camera(pos,target,scale):
    cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
def render(name):
    scene.render.filepath=str(R/(name+'.png'));bpy.ops.render.render(write_still=True)
camera((330,370,325),(80,86,25),302)
bpy.ops.wm.save_as_mainfile(filepath=str(D/'analog_matrix_package.blend'))
render('enclosure_assembled')
camera((320,-120,180),(137,30,21),145)
render('power_entry_assembled')
case['signal_cover'].location.z=64;case['power_hood'].location.z=82
camera((330,360,320),(80,83,57),375)
render('enclosure_exploded')
for o in list(case.values())+lidlabels+hoodlabels+feet+fasteners: o.hide_render=True
for o in scene.objects:
    if o.parent and o.parent.name in case:o.hide_render=True
for o in sinks:o.hide_render=False
for o in retainers:o.hide_render=True
camera((305,350,325),(80,85,14),278)
render('populated_pcb')
camera((330,-160,240),(126,31,20),118)
render('power_entry_detail')
print('Rendered populated PCB, assembled housing and exploded assembly.')
