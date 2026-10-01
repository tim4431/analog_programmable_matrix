"""Package the verified Rev D / M3 mechanical deliverables."""
from pathlib import Path
import json,shutil,zipfile,hashlib,html,subprocess
import trimesh
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'mechanical/analog_matrix_package_m3'
checks=json.loads((D/'mechanical_checks.json').read_text())
assert checks['solid_intersections']==[] and all(checks['case_solid_validity'].values())
assert not json.loads((D/'connector_access_checks.json').read_text())['connector_neighbor_and_cable_intersections']
assert not json.loads((D/'drc_3d_board.json').read_text(encoding='utf-8'))['violations']
meshchecks={}
for p in (D/'print').glob('*.stl'):
    m=trimesh.load_mesh(p)
    meshchecks[p.name]={'watertight':bool(m.is_watertight),'positive_volume':bool(m.volume>0),
      'shells':len(m.split()),'dimensions_mm':[round(float(v),3) for v in m.extents]}
    assert m.is_watertight and m.volume>0 and len(m.split())==1,p
(D/'print_mesh_checks.json').write_text(json.dumps(meshchecks,indent=2))
notes='''ANALOG MATRIX 4x4 - PCB REV D / ENCLOSURE M3

WHAT CHANGED
PCB Rev D is 160 x 170 mm versus Rev C 180 x 210: 28.04% less board area.
Enclosure M3 is 180 x 192 x 60 mm versus M2 200 x 232 x 60: 25.52% less
footprint. Four 2.5 mm feet make overall nominal body height 62.5 mm.
Eight upward-facing 50-ohm BNCs retain 30 mm row spacing and accessible
coupling sleeves. Amphenol 031-5329-52RFX centers: PCB X=7 / 154,
Y=20,50,80,110. Inputs remain high impedance unless optional shunts are fitted.
Outputs retain 49.9-ohm series source termination and require external loads.
Power J9 faces +X at the right board edge, with a matching 20 x 13 mm opening.
The PCB control/power bay is rearranged and the four analog rows are closer.
The sink envelopes remain 35 x 13 x 38.1 mm; temperature qualification must
use this smaller enclosure and the final purchased heatsinks.

OPEN THESE FILES
cad/complete_assembly.step     PCB, enclosure and heatsink clearance models
cad/populated_pcb.step         Actual drilled PCB plus all 424 fitted parts
analog_matrix_4x4_3d.kicad_pcb Portable KiCad PCB with local models
analog_matrix_package.blend    Editable render scene, saved assembled
print/*.stl                    Three printable enclosure parts, in mm
cad/G10_heatsink_retainer.dxf  1:1 machining profile for 3 mm G10
mechanical_dimensions.svg      Dimensioned overview
panel_graphics_1to1.svg        Signal-cover labels at 1:1
THERMAL_CALCULATION.txt        Heat budget and smaller-sink acceptance

COORDINATES AND HEIGHTS
CAD X = PCB X; CAD Y = 170 - KiCad Y. Z=0 is the tray underside.
PCB underside Z=9; actual native stack thickness 1.62; PCB top Z=10.62.
Fabrication remains nominal 1.6 mm. Use this native stack for mechanical fit.
Tray floor 3; insulating bosses 6 above floor. Walls nominally 3 mm thick.
Signal lid top Z=19; ribs extend to Z=13.5. Hood roof top Z=60, inside Z=57.
Eight BNC apertures are diameter 18. Nominal connector ends are Z=27.22,
8.22 mm above the lid. Cable envelopes allow <=17 mm coupling-sleeve OD.
Power window is CAD Y=22..42, Z=12.5..25.5 in the right wall.
The three screw heads are accessed from above with the power hood removed.
USB opening remains 20 x 12 mm; use cable overmould <=18 x 10 mm.

POWER POLARITY - DO NOT INFER FROM THE OLD RENDER
J9 pin 1: +15 V, PCB (155,143), CAD Y=27.
J9 pin 2: GND, PCB (155,137.92), CAD Y=32.08.
J9 pin 3: -15 V, PCB (155,132.84), CAD Y=37.16.
The terminal pin pitch is 5.08 mm. Use the PCB markings and pin numbers.
Disconnect power before wiring. Remove the hood to tighten the top screws.
Use insulated leads up to 3 mm OD in the checked access envelopes and add
external cable strain relief so cable pulls are not carried by solder joints.
The former M12 gland is removed; this is a dry, indoor laboratory enclosure.

PRINT AND ASSEMBLE
Use PA12 SLS/MJF as an initial material/process candidate. Qualify its actual
temperature rating and creep against measured internal temperatures.
The files are mm, 100% scale; largest printed part is 180 x 192 mm.
Covers are supplied roof-down and tray floor-down. For FDM, assess supports
and screw-boss strength. First inspect connector/mount centers to +/-0.25 mm.
16 insert pilots are diameter 4.2. Select matching M3 inserts, about 4.6 OD
and 4 mm length; establish the fit with a printed coupon before assembly.
Recess the PCB-mount inserts 0.5 mm and cover inserts approximately 0.3 mm.
Trim all soldered leads to <=2.5 mm below the board; TO-220 models show this.
Use the original Pico with 8.5 mm female sockets and 2.5 mm male spacers.
Pico PCB underside is 11 mm above the carrier top; do not change that stack
without checking the USB opening and hood fit.

HARDWARE PER UNIT
3 printed parts: base tray, signal lid, independent rear hood
1 G10/FR4 retaining bridge: 85.6 x 14 x 3, no copper, two diameter 3.4 holes
  at 78.0 pitch. Use supplied STEP/DXF. Do not print this hot restraint.
2 M3 female/female aluminum spacers, length 50, hex <=6 mm across flats
2 temperature-rated soft silicone pads, nominal 14 x 6 x 4.5 mm
  CAD compressed thickness 3.78; set actual preload to the selected sink.
16 M3 inserts, 4 mm long, matching the printed pilots
12 M3 x 6 low-profile screws: 6 PCB mounts + 6 signal-cover fasteners
6 insulating PCB washers, about 0.5-0.8 mm thick
8 M3 x 8 screws: 4 hood fasteners + 4 retainer/post fasteners
  Under-tray screw heads must be <=2 mm high to clear the 2.5 mm feet.
4 adhesive feet, approximately 12 x 12 x 2.5
2 bolted TO-220 heatsinks fitting 35 x 13 x 38.1 envelopes
2 TO-220 insulation/interface kits with screws and insulating shoulder bushes
2 1x20 Pico sockets and 2 matching 1x20 headers as specified above
1 external strain-relief anchor for the power leads, appropriate to the bench

HEATSINK INSTALLATION
Sink X centers 102.46 and 140.46. Mounting front plane CAD Y=13.54 includes
a nominal 0.30 mm interface behind the modeled TO-220 rear tab surface.
Sinks start at Z=11.12, end Z=49.22. G10 bridge bottom Z=53, top Z=56.
Post centers CAD (78,-4) and (156,-4), bottom Z=3, top Z=53.
Fit inserts/posts first, mount PCB with insulating washers, bolt the sinks
to regulator tabs, then fit compliant pads and the G10 bridge. Do not preload
the bridge enough to bend the PCB or stress the regulator leads.
L7805 tab is GND; L7905 tab is -15 V. Prevent conductive coupling through
sinks, screws, or support hardware. Qualify the electrical isolation.
The sink fin shapes are reserved envelopes, not a released supplier part.
There are no heatsink locating-pin holes; select a pinless bolted type or
have the supplier provide a compatible mounting arrangement.

VERIFICATION AND LIMITS
KiCad Rev D: zero DRC violations, zero unrouted nets, zero schematic mismatch.
All 1501 electrical pads match the exported schematic. The 36 protected
inverting-node copper geometries retain shape/layers/length after rigid
translation from Rev C. Other routing and placements changed; circuit values
and firmware are unchanged. This does not establish unchanged parasitics.
CAD solid-validity and nominal interference checks pass for the case, PCB,
components, sinks and support hardware. Added checks cover all nine connectors
against neighboring parts, BNC coupling sleeves, and the three power wires.
All three STL files are watertight, single-shell meshes with positive volume.
No prototype print, measured temperature, or post-layout SPICE extraction has
been performed. The inherited A2 SPICE report remains a circuit-level study.
Check actual BNC pin fit and bayonet/cable clearances before a production run.
Do not claim the 38.1 mm sink arrangement thermally qualified until measured.

FILES TO MANUFACTURE
Use Rev D PCB/Gerber/BOM/CPL with M3 mechanics. Earlier revisions are omitted from the public repository.
The Rev D JLCPCB handoff still needs 24 BOM row supplier matches, selected-part
rotation review and via-fill CAM acceptance before an assembly order.
Do not fill electrical connector holes. Follow the via drill rules in the
fabrication notes, including the embedded 0.20 mm thermal holes.

EDITABLE SOURCES / ATTRIBUTION
build_package.py rebuilds CAD with CadQuery 2.8 and the included geometry/models.
render_package.py rebuilds the Blender 4.3 scene from the CAD tessellations.
Standard component models: KiCad library; retain KiCad_models_LICENSE.md.
BNC, Pico and sink clearance models are locally authored, simplified envelopes.
BNC footprint dimensions: Amphenol catalog page 118, Fig 2 / pattern F:
https://www.farnell.com/datasheets/1942962.pdf
Active 50-ohm BNC product:
https://www.amphenolrf.com/en-us/part/031-5329-52rfx/1877/
'''
(D/'ASSEMBLY_AND_PRINTING.txt').write_text(notes,encoding='utf-8')
thermal='''M3 COMPACT ENCLOSURE - ESTIMATE AND ACCEPTANCE, NOT A THERMAL TEST

Nominal external analog supply: +15 V / -15 V. L7805CV and L7905CV generate
+5 V / -5 V. The high-current THS3091 output drivers run from +/-15 V directly.

IDLE BUDGET
16 ADA4899-1 at 14.7 mA typical: 235.2 mA per rail.
16 OPA810 at 3.7 mA typical: 59.2 mA per rail.
These two groups total 294.4 mA through each +/-5 V rail, before trim and
reference devices and regulator ground current. This is not a maximum limit.
Each regulator loses about (15-5)*0.30 = 3.0 W at idle.
Front-end IC heat is roughly 10*0.2944 = 2.94 W; the two regulators add
roughly 6 W. Four THS3091s add about 1.14 W idle, making approximately 10 W
analog board heat at idle, excluding the USB-powered controller and small
ancillary losses. A 1 MHz signal does not make the supply loss negligible.

M3 DESIGN POINT
The smaller board and case retain the same electrical heat budget. Reduced
surface area and airflow paths require renewed thermal qualification.
Reserve 4 W per regulator to allow signal-loading and quiescent variation.
This is an engineering allowance, not a proven worst-case rail current.
For a 35 C room, use:
Tj = Troom + Preg * (R_sink_to_room + R_interface + R_junction_case)
   = 35 + 4*(14 + 2 + 5) = 119 C.
The 5 C/W TO-220 junction-case value is in both ST regulator datasheets.
14 C/W must be an EFFECTIVE sink-to-room value with both regulators operating
in the complete enclosure. It includes air warming and enclosure restriction.
The interface must provide <=2 C/W under the selected mounting pressure.
Target <=120 C estimated junction, below the L7805CV 125 C operating ceiling.

38.1 MM FEASIBILITY
Wakefield's 637-series catalog gives a 34.9 x 12.7 x 38.1 mm example with
65 C rise at 6 W in natural convection, about 10.8 C/W at that test point.
That supports exploring a 38.1 mm class sink; it does not rate our modeled
fin geometry, lower-power convection, insulated mounting, or enclosure.
The catalog example has PCB pins; it is NOT selected as a drop-in BOM part.
Choose a compatible pinless bolted sink or a supplier-approved adaptation.

FIRST-ARTICLE THERMAL ACCEPTANCE
At the warmest intended ambient (design point 35 C), test both rails under
the highest measured loading across matrix settings and simultaneous inputs.
Include full DC output cases and 1 MHz waveforms with four external 50-ohm loads.
Measure regulator input/output current, voltage drop and stabilized case/sink
temperatures with the complete enclosure and representative cables installed.
Compute actual regulator loss including ground current. Require <=4 W each
for this design point; if higher, recalculate and change cooling before use.
At 4 W / 35 C, sink base temperature must be <=91 C (35+4*14); case temperature
must be <=99 C for a <=2 C/W interface. Estimate Tj from measured case + P*5.
Require Tj<=120 C, stable +/-5 V, no thermal shutdown, and enclosure materials
within their published temperature/creep ratings. Check all other devices too.
If those limits are missed, use a better sink/ventilation or reduce regulator
input voltage with a redesigned preregulator. Do not approve by height alone.

PRIMARY SOURCES
https://www.analog.com/en/products/ada4899-1.html
https://www.ti.com/product/OPA810
https://www.st.com/resource/en/datasheet/l78.pdf
https://www.st.com/resource/en/datasheet/l79.pdf
https://wakefieldthermal.com/content/data_sheets/292.pdf
'''
(D/'THERMAL_CALCULATION.txt').write_text(thermal,encoding='utf-8')
# A dimensioned drawing uses the same M3 CAD coordinates.
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="900" viewBox="0 0 1200 900">',
 '<rect width="1200" height="900" fill="#f7f9fa"/>',
 '<style>text{font-family:Arial,sans-serif;fill:#21323e} .dim{stroke:#537183;stroke-width:1;fill:none}</style>']
def line(x1,y1,x2,y2,stroke='#537183',width=1):svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{width}"/>')
def label(x,y,t,size=15,anchor='start'):svg.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}">{html.escape(t)}</text>')
def rect(x,y,w,h,fill,stroke='#537183'):svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}"/>')
label(50,52,'ANALOG MATRIX / COMPACT PACKAGE M3',28)
label(50,81,'PCB revision D  |  Dimensions in mm  |  Nominal prototype geometry',16)
sc=2.8;ox=95;oy=135
X=lambda x:ox+(x+10)*sc
Y=lambda y:oy+(180-y)*sc
rect(X(-10),Y(180),180*sc,192*sc,'#e8edef')
rect(X(0),Y(170),160*sc,170*sc,'#deeee5','#558577')
rect(X(-10),Y(47.7),180*sc,59.7*sc,'#a8b6bd')
line(X(-10),Y(48),X(170),Y(48))
for x in [7,154]:
 for y in [150,120,90,60]:
  svg.append(f'<circle cx="{X(x)}" cy="{Y(y)}" r="{9*sc}" fill="#fff" stroke="#537183"/>')
  line(X(x)-6,Y(y),X(x)+6,Y(y));line(X(x),Y(y)-6,X(x),Y(y)+6)
for x,y in [(4,166),(156,166),(4,44),(156,44),(4,4),(156,20)]:svg.append(f'<circle cx="{X(x)}" cy="{Y(y)}" r="{1.6*sc}" fill="#21323e"/>')
for y in [150,120,90,60]:label(X(25),Y(y)+5,'a'+str(int((150-y)/30)),14);label(X(132),Y(y)+5,'b'+str(int((150-y)/30)),14)
label(X(80),Y(107),'SIGNAL COVER',18,'middle');label(X(80),Y(102),'8 x diameter 18 access',13,'middle')
label(X(80),Y(32),'REMOVABLE POWER HOOD',15,'middle')
line(X(170),Y(22),X(170),Y(42),'#e28d36',5)
line(X(-10),Y(19),X(-10),Y(39),'#e28d36',5)
line(X(-10),Y(187),X(170),Y(187));label(X(80),Y(191),'180.0',17,'middle')
for x in [-10,170]:line(X(x),Y(184),X(x),Y(190))
line(X(-19),Y(-12),X(-19),Y(180));label(ox-66,oy+270,'192.0',17)
label(ox,oy+192*sc+32,'TOP VIEW   PCB outline 160 x 170; connector pitch 30',16)
label(690,155,'SIDE PROFILE',18)
ss=1.9;xx=700;zz=440
rect(xx,zz-16*ss,192*ss,16*ss,'#a8b6bd')
rect(xx,zz-60*ss,59.7*ss,43.7*ss,'#758b96')
rect(xx+60*ss,zz-19*ss,132*ss,3*ss,'#dce3e5')
for y in [72,102,132,162]:rect(xx+(y-5.5)*ss,zz-27.22*ss,11*ss,16.6*ss,'#c2c9cd')
line(xx+202*ss,zz,xx+202*ss,zz-60*ss);label(xx+204*ss,zz-28*ss,'60',16)
label(700,481,'Body height 60; with feet 62.5',16)
label(700,514,'BNC tips: 8.22 above signal cover',16)
label(700,547,'Sink envelopes: 35 x 13 x 38.1 each',16)
label(700,580,'Right power opening: 20 x 13',16)
label(700,613,'Left USB opening: 20 x 12',16)
label(700,646,'6 x PCB mounting holes, diameter 3.2',16)
label(50,768,'PCB area: -28.04%   |   Enclosure footprint: -25.52%   |   Height retained for cooling',20)
label(50,807,'Use M3 enclosure with PCB D only. Nominal solid/cable checks pass; verify physical fit and full-load temperatures.',16)
label(50,836,'STEP files define geometry. Heatsink fins are clearance envelopes, not a qualified thermal part.',16)
svg.append('</svg>');(D/'mechanical_dimensions.svg').write_text(''.join(svg),encoding='utf-8')
# Printable artwork uses the CAD datum and the same lettering as the render.
labels=['<svg xmlns="http://www.w3.org/2000/svg" width="180mm" height="192mm" viewBox="-10 -10 180 192">',
 '<g font-family="Arial,sans-serif" text-anchor="middle" fill="#102a3b">']
def panel_label(t,x,y,size):
    y=170-y
    labels.append(f'<text x="{x}" y="{y}" font-size="{size}" transform="rotate(180 {x} {y})">{html.escape(t)}</text>')
panel_label('ANALOG MATRIX',80,155,6.2);panel_label('4 x 4 / DC - 1 MHz',80,165,3.1)
panel_label('b = M a',80,101,6.5);panel_label('STATIC COEFFICIENTS -1 TO +1',80,112,2.3)
for i,y in enumerate([20,50,80,110]):
    panel_label('a'+str(i),24,170-y+1,4.2);panel_label('b'+str(i),135,170-y+1,4.2)
panel_label('INPUT +/-1 V',39,53,2.8);panel_label('OUTPUT 50 ohm',121,53,2.8)
labels.extend(['</g>','</svg>']);(D/'panel_graphics_1to1.svg').write_text('\n'.join(labels),encoding='utf-8')
port='<svg xmlns="http://www.w3.org/2000/svg" width="20mm" height="4mm" viewBox="0 0 20 4"><g font-family="Arial,sans-serif" font-size="1.7" text-anchor="middle" fill="#ffffff">'
for x,t in [(5,'+15V'),(10.08,'GND'),(15.16,'-15V')]:port+=f'<text x="{x}" y="2.7">{t}</text>'
(D/'power_port_label_1to1.svg').write_text(port+'</g></svg>')
subprocess.run([r'C:\Program Files\Inkscape\bin\inkscape.com',str(D/'mechanical_dimensions.svg'),'--export-type=png','--export-filename='+str(D/'mechanical_dimensions.png')],check=True,capture_output=True)
source=ROOT/'pcb/analog_matrix_4x4_rev_d/analog_matrix_4x4.kicad_pcb'
assert hashlib.sha256(source.read_bytes()).hexdigest()==checks['pcb_source_sha256']
manifest={str(p.relative_to(D)):hashlib.sha256(p.read_bytes()).hexdigest() for p in D.rglob('*')
 if p.is_file() and p.name!='SHA256.json' and p.suffix not in ['.blend1','.kicad_prl','.lck']}
(D/'SHA256.json').write_text(json.dumps(manifest,indent=2))
archive=ROOT/'output/analog_matrix_3d_and_enclosure_M3.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for name in list(manifest)+['SHA256.json']:z.write(D/name,str(Path(D.name)/name))
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'mesh_checks':meshchecks},indent=2))
