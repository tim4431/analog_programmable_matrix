"""Verify the LC1 release artifacts without changing either hardware design."""
from pathlib import Path
import csv,hashlib,json,re,zipfile,subprocess,sys
R=Path(__file__).resolve().parents[1];REPO=R.parents[1];H=R/'hardware';A=R/'assembly'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
assert sha(REPO/'pcb/analog_matrix_4x4_rev_d/analog_matrix_4x4.kicad_pcb')=='0bc346aeb27012868bfcf66266c1a55381e648ed224be89ea83ef740c1c2d8b5'
assert sha(REPO/'pcb/analog_matrix_4x4_rev_d/firmware/main.py')=='1a9366989ff59926f5347e38f65bada00d3ea09619686d82721428ee7eb28210'
assert all(not sheet['violations'] for sheet in load(H/'erc.json')['sheets'])
assert not load(H/'connectivity_audit.json')['connectivity_errors']
assert not load(H/'footprint_audit.json')['pad_number_errors']
assert all(not load(H/'drc.json')[key] for key in ['violations','unconnected_items','schematic_parity'])
pcb_hash=sha(H/'analog_matrix_lc1.kicad_pcb')
layout=load(H/'layout_review.json');assert layout['source_pcb_sha256']==pcb_hash
assert layout['tracks_on_ground_layer']==0 and layout['ground_plane_connected_regions']==1
assert len(layout['mdac_current_output_routes'])==16
checks=load(A/'assembly_checks.json');assert checks['source_pcb_sha256']==pcb_hash
assert checks['fabrication_export_checks_passed'] and not checks['hardware_qualified']
assert checks['smt']==365 and checks['manual']==18 and checks['dnp']==4
readcsv=lambda p:list(csv.DictReader(p.open(encoding='utf-8-sig')))
bom=readcsv(A/'BOM_JLCPCB.csv');cpl=readcsv(A/'CPL_JLCPCB.csv')
assert len(cpl)==365 and len(bom)==35
assert {ref for row in bom for ref in row['Designator'].split(',')}=={row['Designator'] for row in cpl}
assert all(row['Layer']=='Top' for row in cpl)
mechanical=load(R/'mechanical/mechanical_checks.json')
assert mechanical['pcb_source_sha256']==pcb_hash and not mechanical['solid_intersections']
assert mechanical['populated_components']==383
for name in ['populated_pcb','enclosure_assembled','enclosure_exploded']:assert (R/'mechanical/renders'/f'{name}.png').stat().st_size>100000
manifest=load(H/'fabrication/SHA256.json')
for name,digest in manifest.items():assert sha(H/'fabrication'/name)==digest,name
archive=A/'Gerber_JLCPCB_LC1.zip';assert sha(archive)==checks['gerber_zip_sha256']
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None and set(z.namelist())==set(manifest)
 for name,digest in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
results=load(R/'simulation/results.json');assert len(results)==35
for result in results:
 assert result['status']=='completed' and result['returncode']==0,result['bench']
 assert sha(R/'simulation/benches'/result['bench'])==result['sha256'],result['bench']
 assert result['evidence_matches_netlist']
for page in [R/'README.md',R/'SOURCING.md',R/'firmware/CONTROL.md',REPO/'README.md']:
 for link in re.findall(r'\]\(([^)]+)\)',page.read_text(encoding='utf-8')):
  if '://' not in link and not link.startswith('#'):assert (page.parent/link.split('#')[0]).exists(),(page.name,link)
subprocess.run([sys.executable,str(R/'tools/test_firmware.py')],check=True)
print('PASS: LC1 ERC/DRC/parity, BOM/CPL, Gerber hashes, mechanical source, 35 completed simulation benches, firmware and documentation; original PCB preserved.')
