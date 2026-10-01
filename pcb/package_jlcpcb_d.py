"""Deterministic manufacturing-format CSV export, not a procurement approval.
Uses the exact PCB coordinates and manufacturer's required machine headers.
"""
from pathlib import Path
import csv,json,zipfile,shutil,hashlib,collections,re
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'pcb/analog_matrix_4x4_rev_d'
O=ROOT/'output/jlcpcb_rev_d';O.mkdir(parents=True,exist_ok=True)
parts=json.loads((D/'design_instances.json').read_text())['parts']
geo={p['ref']:p for p in json.loads((ROOT/'mechanical/analog_matrix_package_m3/pcb_geometry.json').read_text())['parts']}
pos={p['Ref']:p for p in csv.DictReader((D/'placement_front.csv').open(encoding='utf-8-sig'))}
report=json.loads((D/'drc.json').read_text())
assert not any(report[k] for k in ['violations','unconnected_items','schematic_parity'])
codes={
 'AD5544BRSZ':('C649815','https://www.lcsc.com/product-detail/C649815.html'),
 'TMUX6219DGKR':('C2876423','https://www.lcsc.com/product-detail/C2876423.html'),
 'ADA4899-1YRDZ':('C654315','https://www.lcsc.com/product-detail/C654315.html'),
 'THS3091DDAR':('C181226','https://www.lcsc.com/product-image/C181226.html?whichImg=0'),
 'OPA197ID':('C1347124','https://www.lcsc.com/product-detail/C1347124.html'),
 'ADR4525BRZ':('C395112','https://lcsc.com/product-detail/New-Arrivals_Analog-Devices-ADI-ADR4525BRZ_C395112.html')}

def csvfile(name,header,rows):
    with (O/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(header);w.writerows(rows)
def sortref(p):return (re.match('[A-Z]+',p['ref']).group(),int(re.search(r'\d+',p['ref']).group()))
smt=sorted([p for p in parts if not p['dnp'] and geo[p['ref']]['smd']],key=sortref)
manual=sorted([p for p in parts if not p['dnp'] and not geo[p['ref']]['smd']],key=sortref)
dnp=sorted([p for p in parts if p['dnp']],key=sortref)
groups=collections.defaultdict(list)
for p in smt:groups[(p['value'],p['footprint'],p['rating'])].append(p['ref'])
bom=[];matching=[]
for (value,fp,rating),refs in groups.items():
    code,url=codes.get(value,('',''))
    comment=value+(' / '+rating if rating else '')
    bom.append([comment,','.join(refs),fp.split(':')[1],code])
    matching.append([','.join(refs),len(refs),value,fp.split(':')[1],rating,code,
        'Confirm JLC assembly availability and reel orientation' if code else 'Select exact supplier part before purchase',url])
csvfile('BOM_JLCPCB.csv',['Comment','Designator','Footprint','LCSC Part #'],bom)
cpl=[]
for p in smt:
    r=pos[p['ref']];g=geo[p['ref']]
    assert abs(float(r['PosX'])-g['x'])<1e-6 and abs(float(r['PosY'])+g['y'])<1e-6
    cpl.append([p['ref'],f"{float(r['PosX']):.6f}",f"{float(r['PosY']):.6f}",'Top',f"{float(r['Rot'])%360:.6f}"])
csvfile('CPL_JLCPCB.csv',['Designator','Mid X','Mid Y','Layer','Rotation'],cpl)
csvfile('PART_MATCHING.csv',['Designator','Quantity','Required part/value','Package','Required rating','LCSC Part #','Action','Supplier identity source'],matching)
csvfile('MANUAL_ASSEMBLY.csv',['Designator','Quantity','Part/value','Footprint','Rating'],
    [[p['ref'],1,p['value'],p['footprint'].split(':')[1],p['rating']] for p in manual])
csvfile('DO_NOT_POPULATE.csv',['Designator','Value','Reason'],[[p['ref'],p['value'],'Optional input termination; default input is high impedance'] for p in dnp])

# Pin-1 locations give an independent audit for the assembler's rotation view.
pins=[]
for p in smt:
    g=geo[p['ref']]
    if p['ref'].startswith('U') or p.get('polarized'):
        pad=next((pad for pad in g['pads'] if pad['number']=='1'),None)
        if pad:pins.append([p['ref'],g['x'],-g['y'],g['rotation']%360,pad['x'],-pad['y'],p['value']])
csvfile('PIN1_ORIENTATION_REFERENCE.csv',['Designator','Center X mm','Center Y mm','KiCad rotation deg','Pin 1 X mm','Pin 1 Y mm','Value'],pins)

# Bare-board upload contains only actual manufacturing layers and drill files.
manufacturing=[]
with zipfile.ZipFile(O/'Gerber_JLCPCB.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in (D/'fabrication').iterdir():
        if p.suffix.lower() in ['.gtl','.gbl','.g2','.g3','.gts','.gbs','.gto','.gbo','.gtp','.gm1','.drl','.gbrjob']:
            z.write(p,p.name);manufacturing.append(p.name)
for name in ['assembly_front.svg','pcb_top_view.png','FABRICATION_AND_BRINGUP.txt','via_in_pad_locations.csv']:
    shutil.copy2(D/name,O/name)
text=f'''ANALOG MATRIX REV D - JLCPCB UPLOAD

UPLOAD FILES
1. Gerber_JLCPCB.zip: bare PCB fabrication upload. Four copper layers and
   separate plated/non-plated drills. Do not upload this whole handoff ZIP.
2. BOM_JLCPCB.csv: top-side SMT assembly component matching.
3. CPL_JLCPCB.csv: top-side SMT component placement, millimetres.

These files have been checked for matching reference designators. They are
ready for upload and quotation; component selection and CAM acceptance must
be completed before paying for an assembled-board order.

ASSEMBLY SCOPE
{len(smt)} fitted SMT components in {len(bom)} BOM rows; all on the TOP side.
{len(manual)} through-hole/module items listed separately in MANUAL_ASSEMBLY.csv.
{len(dnp)} deliberately omitted resistors in DO_NOT_POPULATE.csv.
Pico installation additionally needs two 1x20 sockets and two mating 1x20
headers. Heatsinks, insulation, supports and enclosure hardware are separate.

PART MATCHING
Six IC ordering codes have supplier identity matches, with source links in
PART_MATCHING.csv. These are identity checks, not reserved JLC inventory.
{sum(1 for r in bom if not r[3])} BOM rows still need exact supplier part matching, including OPA810ID,
SN74HC595D and passive parts. Blank LCSC cells are intentional, never dummy
numbers. Match all values, dielectric, tolerance, voltage, power and package.
Do not replace the 0.1% thin-film resistors with generic 1% resistors.
Do not replace a PowerPAD amplifier with a non-exposed-pad version.
Small 2.2pF capacitors must be C0G/NP0, tolerance +/-0.1pF.
The output 49.9-ohm 2512 resistors must be at least 1W.
Tantalum/capacitor voltage and case size need exact part verification.

BOARD ORDER SETTINGS
160 x 170 mm; 4 layers; nominal 1.6 mm FR-4; Tg >=150C; ENIG recommended.
L1 top signals, L2 GND, L3 signals/power, L4 bottom signals/GND.
Select 35um copper on all four layers or have CAM confirm the chosen stack.
No controlled impedance service is required by this release.
Minimum 0.15mm trace/clearance; minimum drill 0.20mm; min annular ring 0.10mm.
Use epoxy-filled and copper-capped via-in-pad service (POFV), not ordinary
tenting or soldermask plugging. Get explicit CAM acceptance for this 4-layer
board and the small thermal holes before releasing the order.

VIA FILL INSTRUCTIONS FOR CAM
All plated drills <=0.30mm are vias and should be filled and copper capped.
The 0.20mm holes tagged ComponentDrill under THS3091 are thermal vias and
must ALSO be filled/capped, despite that automatic drill attribute.
Do not fill actual component lead holes >=0.80mm or any NPTH mounting hole.
The conservative via_in_pad_locations.csv map is supplied for review.
Ask CAM to provide the processed via-fill/drill plot for confirmation.

PLACEMENT COORDINATES
The CPL preserves native Gerber coordinates: X is rightward and Y is
negative downward from the PCB top-left (0,0). This is intentional and
matches these Gerbers. All rotations are KiCad CCW normalized to 0..359.
JLC library zero-angle conventions can differ by selected part. Verify
polarized devices and ALL IC pin-1 marks in the JLC placement preview.
Use PIN1_ORIENTATION_REFERENCE.csv and assembly_front.svg as the reference.
No vendor-specific angle corrections have been guessed. Do not approve an
assembly until each selected library part is aligned in that preview.

MECHANICAL HAND ASSEMBLY
The PCB uses vertical Amphenol 031-5329-52RFX 50-ohm BNC connectors.
Use the supplied Rev D footprint; verify purchased-part fit on first article.
J9 power wire entry faces the right edge. Its pin order remains +15V/GND/-15V.
Use the separate M3 enclosure with this PCB. The smaller 38.1 mm sink envelope
is subject to full-load thermal qualification; see FABRICATION_AND_BRINGUP.txt.
Trim soldered leads to <=2.5mm below PCB for the accompanying enclosure.
Install regulator heatsinks and insulators before operation. Negative
regulator tab is -15V, not ground. See FABRICATION_AND_BRINGUP.txt.

VALIDATION
Native PCB DRC: zero violations, zero unrouted, zero schematic mismatches.
BOM and CPL reference sets match exactly; DNP and manual parts excluded.
This is an unbuilt electrical prototype; hardware performance is unmeasured.

FORMAT AND PROCESS SOURCES
https://jlcpcb.com/help/article/bill-of-materials-for-pcb-assembly
https://jlcpcb.com/help/article/how-to-generate-the-bom-and-centroid-file-from-kicad
https://jlcpcb.com/help/article/pcb-via-covering
https://github.com/JLCPCB/JLCPCB-SMT-Assembly-Components-orientation-fix
'''
(O/'START_HERE.txt').write_text(text,encoding='utf-8')
assert {r for row in bom for r in row[1].split(',')}=={r[0] for r in cpl}
assert len({r[0] for r in cpl})==len(cpl)
assert len(smt)+len(manual)+len(dnp)==len(parts)==428
check={'fitted_smt':len(smt),'smt_bom_rows':len(bom),'supplier_identity_matches':len(codes),
 'unmatched_bom_rows':sum(not r[3] for r in bom),'manual_items':len(manual),'dnp':len(dnp),
 'bom_cpl_references_identical':True,'duplicate_cpl_references':0,
 'gerber_files':manufacturing,'source_pcb_sha256':hashlib.sha256((D/'analog_matrix_4x4.kicad_pcb').read_bytes()).hexdigest(),
 'order_release_status':'Await component matching, vendor rotation preview and via-fill CAM acceptance'}
(O/'upload_checks.json').write_text(json.dumps(check,indent=2))
with zipfile.ZipFile(ROOT/'output/analog_matrix_rev_d_JLCPCB_handoff.zip','w',zipfile.ZIP_DEFLATED) as z:
    for f in O.iterdir():
        if f.is_file():z.write(f,f.name)
print(json.dumps(check,indent=2))
