"""Read LC1's actual PCB for assembly and mechanical review. Run in KiCad Python."""
from pathlib import Path
import csv, hashlib, json, re
import pcbnew as k
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
P=ROOT/'hardware/analog_matrix_lc1.kicad_pcb';b=k.LoadBoard(str(P))
parts={p['ref']:p for p in json.loads((ROOT/'hardware/design_instances.json').read_text())['parts']}
J=ROOT/'assembly';J.mkdir(exist_ok=True)
rows=[];manual=[];dnp=[];pins=[];groups={};geometry=[]
sort=lambda r:(r[0],int(re.search(r'\d+',r)[0]))
identities={'DAC7811IDGSR':'C390090','MCP4728T-E_UN':'C478093','TMUX6136PWR':'C2673380','OPA2810IDR':'C1849413','OPA4197IPWR':'C2057327'}
for row in csv.DictReader((REPO/'output/jlcpcb_rev_d/PART_MATCHING.csv').open(encoding='utf-8-sig')):
 if row['LCSC Part #']:identities[row['Required part/value']]=row['LCSC Part #']
for f in sorted(b.GetFootprints(),key=lambda f:sort(f.GetReference())):
 ref=f.GetReference()
 if ref not in parts:continue
 p=parts[ref];x,y=(k.ToMM(v) for v in f.GetPosition());angle=f.GetOrientationDegrees()%360
 value=p['value'].replace('MCP4728T-E_UN','MCP4728T-E/UN');fp=str(f.GetFPID().GetLibItemName())
 models=[dict(file=m.m_Filename,offset=[m.m_Offset.x,m.m_Offset.y,m.m_Offset.z],scale=[m.m_Scale.x,m.m_Scale.y,m.m_Scale.z],rotation=[m.m_Rotation.x,m.m_Rotation.y,m.m_Rotation.z]) for m in f.Models()]
 pads=[dict(number=t.GetNumber(),x=k.ToMM(t.GetPosition().x),y=k.ToMM(t.GetPosition().y),sx=k.ToMM(t.GetSize().x),sy=k.ToMM(t.GetSize().y),drill=[k.ToMM(v) for v in t.GetDrillSize()],rotation=t.GetOrientationDegrees(),shape=int(t.GetShape())) for t in f.Pads()]
 geometry.append(dict(ref=ref,value=value,footprint=fp,x=x,y=y,rotation=angle,dnp=p['dnp'],smd=bool(f.GetAttributes()&k.FP_SMD),models=models,pads=pads))
 if p['dnp']:dnp.append([ref,value,fp,p.get('note','')]);continue
 if not f.GetAttributes()&k.FP_SMD:manual.append([ref,value,fp,p.get('note','')]);continue
 rows.append([ref,f'{x:.4f}',f'{-y:.4f}','Top',f'{angle:.4f}'])
 key=(value,fp,p.get('rating',''),identities.get(p['value'],''));groups.setdefault(key,[]).append(ref)
 if ref.startswith('U') or p.get('polarized'):
  t=next(t for t in f.Pads() if t.GetNumber()=='1');pins.append([ref,x,-y,angle,k.ToMM(t.GetPosition().x),-k.ToMM(t.GetPosition().y),value])
def write(name,header,rows):
 with (J/name).open('w',newline='',encoding='utf-8-sig') as stream:
  writer=csv.writer(stream);writer.writerow(header);writer.writerows(rows)
write('CPL_JLCPCB.csv',['Designator','Mid X','Mid Y','Layer','Rotation'],rows)
write('BOM_JLCPCB.csv',['Comment','Designator','Footprint','LCSC Part #'],[(value+(' / '+rating if rating else ''),','.join(refs),fp,lcsc) for (value,fp,rating,lcsc),refs in groups.items()])
write('PART_MATCHING.csv',['Designator','Quantity','Required part/value','Package','Required rating','LCSC Part #','Action'],[(','.join(refs),len(refs),value,fp,rating,lcsc,'Verify exact manufacturer, stock and placement' if lcsc else 'Select exact supplier part') for (value,fp,rating,lcsc),refs in groups.items()])
write('MANUAL_ASSEMBLY.csv',['Designator','Value','Footprint','Note'],manual)
write('DO_NOT_POPULATE.csv',['Designator','Value','Footprint','Note'],dnp)
write('PIN1_ORIENTATION_REFERENCE.csv',['Designator','Center X mm','Center Y mm','KiCad rotation deg','Pin 1 X mm','Pin 1 Y mm','Value'],pins)
assert len(rows)==365 and len(manual)==18 and len(dnp)==4
assert {r[0] for r in rows}=={r for refs in groups.values() for r in refs}
checks=dict(source_pcb_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),smt=len(rows),manual=len(manual),dnp=len(dnp),bom_groups=len(groups),manufacturing_release=False)
(J/'assembly_checks.json').write_text(json.dumps(checks,indent=2))
M=ROOT/'mechanical';M.mkdir(exist_ok=True)
(M/'pcb_geometry.json').write_text(json.dumps(dict(source_sha256=checks['source_pcb_sha256'],width=160,depth=170,thickness=1.62,parts=geometry),indent=2))
print(json.dumps(checks))
