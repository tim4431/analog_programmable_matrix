"""Export fabrication/assembly files only after a clean native PCB DRC."""
from pathlib import Path
import json,subprocess,shutil,csv,collections,zipfile,hashlib
ROOT=Path(__file__).resolve().parent.parent;D=ROOT/'pcb/analog_matrix_4x4_rev_d';OUT=ROOT/'output';FAB=D/'fabrication';FAB.mkdir(exist_ok=True)
CLI=r'C:\Program Files\KiCad\8.0\bin\kicad-cli.exe';board=D/'analog_matrix_4x4.kicad_pcb'
report=json.loads((D/'drc.json').read_text(encoding='utf-8'))
assert not report['unconnected_items'],'PCB still has unrouted connections'
assert not [x for x in report['violations'] if x['severity']=='error'],'PCB has DRC errors'
assert not report['violations'],'Resolve PCB warnings before packaging'
assert not report['schematic_parity'],'PCB metadata differs from the schematic'
def cli(*args):
    r=subprocess.run([CLI,*map(str,args)],capture_output=True,text=True,encoding='utf-8',errors='replace')
    if r.returncode:raise RuntimeError(r.stdout+r.stderr)
    return r.stdout
cli('pcb','export','gerbers','--layers','F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,F.Paste,Edge.Cuts','--subtract-soldermask','--output',str(FAB)+'/',board)
cli('pcb','export','drill','--output',str(FAB)+'/','--format','excellon','--excellon-units','mm','--excellon-separate-th','--generate-map','--map-format','svg',board)
cli('pcb','export','pos','--format','csv','--units','mm','--side','front','--exclude-dnp','--output',D/'placement_front.csv',board)
cli('pcb','export','svg','--layers','F.Cu,F.Silkscreen,Edge.Cuts','--page-size-mode','2','--exclude-drawing-sheet','--output',D/'pcb_front.svg',board)
cli('pcb','export','svg','--layers','B.Cu,Edge.Cuts','--page-size-mode','2','--exclude-drawing-sheet','--output',D/'pcb_back.svg',board)
cli('pcb','export','svg','--layers','F.Fab,F.Silkscreen,Edge.Cuts','--page-size-mode','2','--exclude-drawing-sheet','--output',D/'assembly_front.svg',board)
parts=json.loads((D/'design_instances.json').read_text())['parts'];groups=collections.defaultdict(list)
cli('sch','export','pdf','--output',D/'schematic.pdf',D/'analog_matrix_4x4.kicad_sch')
shutil.copy2(ROOT/'output/pdf/analog_matrix_spice_validation_rev_a2.pdf',D/'circuit_spice_validation_A2.pdf')
for p in parts:groups[p['value'],p['footprint'],p['rating'],p['dnp']].append(p['ref'])
with (D/'assembly_bom.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f);w.writerow(['References','Quantity','Value or IC MPN','Footprint','Rating','Fit'])
    for (value,foot,rating,dnp),refs in groups.items():w.writerow([', '.join(refs),len(refs),value,foot,rating,'DNP' if dnp else 'YES'])
for name in ['FABRICATION_AND_BRINGUP.txt','via_in_pad_locations.csv']:shutil.copy2(D/name,FAB/name)
files={str(p.relative_to(FAB)):hashlib.sha256(p.read_bytes()).hexdigest() for p in FAB.iterdir() if p.is_file() and p.name!='SHA256.json'}
(FAB/'SHA256.json').write_text(json.dumps(files,indent=2))
OUT.mkdir(exist_ok=True)
with zipfile.ZipFile(OUT/'analog_matrix_4x4_rev_d_fabrication.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in FAB.iterdir():
        if p.is_file():z.write(p,p.name)
with zipfile.ZipFile(OUT/'analog_matrix_4x4_rev_d_pcb.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in D.rglob('*'):
        if p.is_file() and not any(x in p.parts for x in ['__pycache__','.git']) and p.suffix not in ['.kicad_prl','.lck'] and '~' not in p.name:z.write(p,str(Path(D.name)/p.relative_to(D)))
print('Exported native project, BOM, placement, previews and fabrication archive.')
