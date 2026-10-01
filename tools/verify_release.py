"""Verify the selected release without changing native design or evidence files."""
from pathlib import Path
import csv,hashlib,json,re

R=Path(__file__).resolve().parents[1]
D=R/'pcb/analog_matrix_4x4_rev_d';M=R/'mechanical/analog_matrix_package_m3';J=R/'output/jlcpcb_rev_d'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
board_hash=sha(D/'analog_matrix_4x4.kicad_pcb')
assert board_hash=='0bc346aeb27012868bfcf66266c1a55381e648ed224be89ea83ef740c1c2d8b5'
assert all(not load(D/'drc.json')[k] for k in ['violations','unconnected_items','schematic_parity'])
assert all(not s['violations'] for s in load(D/'erc.json')['sheets'])
parts=load(D/'design_instances.json')['parts']
assert len(parts)==428 and not {'D3','R147'} & {p['ref'] for p in parts}
assert board_hash==load(M/'mechanical_checks.json')['pcb_source_sha256']
assert not load(M/'mechanical_checks.json')['solid_intersections']
assert all(v['watertight'] and v['shells']==1 for v in load(M/'print_mesh_checks.json').values())
assert not load(R/'mechanical/bnc_access_review_no_led/bnc_access_checks.json')['collisions']
readcsv=lambda p:list(csv.DictReader(p.open(encoding='utf-8-sig')))
bom=readcsv(J/'BOM_JLCPCB.csv');cpl=readcsv(J/'CPL_JLCPCB.csv')
assert {ref for row in bom for ref in row['Designator'].split(',')}=={row['Designator'] for row in cpl}
assert len(cpl)==406
assert board_hash==load(J/'upload_checks.json')['source_pcb_sha256']
for p in (D/'fabrication').iterdir():
 if p.name in load(D/'fabrication/SHA256.json'):assert sha(p)==load(D/'fabrication/SHA256.json')[p.name]
for entry in load(R/'spice/BENCH_MANIFEST.json')['benches']:
 net=R/'spice/benches'/(entry['name']+'.cir')
 assert sha(net)==entry['netlist_sha256'],entry['name']
for page in [R/'README.md',R/'docs/JLCPCB_ORDER_STATUS.md',R/'docs/THIRD_PARTY_NOTICES.md',R/'spice/README.md']:
 for link in re.findall(r'\]\(([^)]+)\)',page.read_text(encoding='utf-8')):
  if '://' not in link and not link.startswith('#'):assert (page.parent/link.split('#')[0]).exists(),(page.name,link)
print('PASS: PCB D, no added LED, stored ERC/DRC, CAD/mesh checks, 406 BOM/CPL references, final simulation netlists and documentation links.')
