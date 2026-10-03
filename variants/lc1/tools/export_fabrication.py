"""Export quote/fabrication files only after native DRC and parity pass.

Run using KiCad's Python. Source board and exports are hashed together.
"""
from pathlib import Path
import argparse,csv,hashlib,json,subprocess,zipfile
import pcbnew as k
ROOT=Path(__file__).resolve().parents[1];H=ROOT/'hardware';A=ROOT/'assembly'
args=argparse.ArgumentParser();args.add_argument('--kicad',default=r'C:\Program Files\KiCad\8.0\bin\kicad-cli.exe');opts=args.parse_args()
P=H/'analog_matrix_lc1.kicad_pcb';F=H/'fabrication';F.mkdir(exist_ok=True)
def run(*args):subprocess.run([opts.kicad,*map(str,args)],check=True)
run('pcb','drc','--format','json','--schematic-parity','--exit-code-violations','--output',H/'drc.json',P)
report=json.loads((H/'drc.json').read_text(encoding='utf-8'))
assert all(not report[key] for key in ['violations','unconnected_items','schematic_parity']), 'Unresolved native PCB check'
run('pcb','export','gerbers','--layers','F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts','--exclude-value','--subtract-soldermask','--output',str(F)+'/',P)
run('pcb','export','drill','--format','excellon','--drill-origin','absolute','--excellon-units','mm','--excellon-separate-th','--output',str(F)+'/',P)
run('pcb','export','svg','--layers','F.Fab,F.SilkS,Edge.Cuts','--page-size-mode','2','--exclude-drawing-sheet','--output',A/'assembly_front.svg',P)
b=k.LoadBoard(str(P));pads=[p for f in b.GetFootprints() for p in f.Pads() if p.GetAttribute()==k.PAD_ATTRIB_SMD]
locations=[]
for t in b.GetTracks():
 if not isinstance(t,k.PCB_VIA):continue
 position=t.GetPosition();diam=k.ToMM(t.GetWidth());overlap=[]
 for p in pads:
  box=p.GetBoundingBox();box.Inflate(k.FromMM(diam/2))
  if box.Contains(position):overlap.append(p.GetParentFootprint().GetReference()+'.'+p.GetNumber())
 if overlap:locations.append([k.ToMM(position.x),k.ToMM(position.y),k.ToMM(t.GetDrillValue()),diam,'via',','.join(sorted(set(overlap)))])
for f in b.GetFootprints():
 for p in f.Pads():
  drill=k.ToMM(p.GetDrillSize().x)
  if 0<drill<=.3:locations.append([k.ToMM(p.GetPosition().x),k.ToMM(p.GetPosition().y),drill,k.ToMM(p.GetSize().x),'thermal component drill',f.GetReference()+'.'+p.GetNumber()])
with (A/'via_in_pad_locations.csv').open('w',newline='',encoding='utf-8-sig') as stream:
 w=csv.writer(stream);w.writerow(['X mm','Y mm','Drill mm','Diameter mm','Kind','Overlapping pad envelopes']);w.writerows(locations)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest={p.name:sha(p) for p in F.iterdir() if p.is_file() and p.name!='SHA256.json'}
(F/'SHA256.json').write_text(json.dumps(manifest,indent=2))
archive=A/'Gerber_JLCPCB_LC1.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for name in manifest:z.write(F/name,name)
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
checks=json.loads((A/'assembly_checks.json').read_text());assert checks['source_pcb_sha256']==sha(P),'Refresh assembly metadata after PCB changes'
checks.update(native_drc_violations=0,unrouted=0,schematic_mismatches=0,gerber_zip_sha256=sha(archive),fabrication_export_checks_passed=True,hardware_qualified=False,via_in_pad_review_locations=len(locations))
(A/'assembly_checks.json').write_text(json.dumps(checks,indent=2))
print('LC1 exports checked; CAM/part matching and prototype qualification still required.')
