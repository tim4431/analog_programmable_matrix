"""Final geometry statistics and assembly map for filled/capped vias."""
from pathlib import Path
import pcbnew as k,json,csv,collections,hashlib,xml.etree.ElementTree as ET
R=Path(__file__).resolve().parent.parent;D=R/'pcb/analog_matrix_4x4_rev_d';b=k.LoadBoard(str(D/'analog_matrix_4x4.kicad_pcb'))
xy=lambda p:(k.ToMM(p.x),k.ToMM(p.y))
pads=[(f,p) for f in b.GetFootprints() for p in f.Pads() if p.GetAttribute()==k.PAD_ATTRIB_SMD and p.IsOnLayer(k.F_Cu)]
holes=[]
for t in b.GetTracks():
    if isinstance(t,k.PCB_VIA):holes.append((*xy(t.GetPosition()),k.ToMM(t.GetDrill()),k.ToMM(t.GetWidth()),t.GetNetname(),'via'))
for f in b.GetFootprints():
    for p in f.Pads():
        if 0<k.ToMM(p.GetDrillSize().x)<=.25:holes.append((*xy(p.GetPosition()),k.ToMM(p.GetDrillSize().x),k.ToMM(p.GetSize().x),p.GetNetname(),f.GetReference()+'.'+p.GetNumber()))
mapped=[]
for x,y,drill,diam,net,kind in holes:
    hits=[]
    for f,p in pads:
        if p.GetNetname()!=net:continue
        q=p.GetBoundingBox();lo=xy(q.GetOrigin());hi=(k.ToMM(q.GetRight()),k.ToMM(q.GetBottom()));extra=drill/2+.03
        if lo[0]-extra<=x<=hi[0]+extra and lo[1]-extra<=y<=hi[1]+extra:hits.append(f.GetReference()+'.'+p.GetNumber())
    if hits:mapped.append([round(x,4),round(y,4),drill,diam,net,', '.join(sorted(set(hits))),kind])
with (D/'via_in_pad_locations.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f);w.writerow(['X from left mm','Y from top mm','Finished hole mm','Copper diameter mm','Net','Nearby SMD land','Origin']);w.writerows(mapped)
info=json.loads((D/'pcb_audit.json').read_text());counts=collections.Counter(b.GetLayerName(t.GetLayer()) for t in b.GetTracks() if not isinstance(t,k.PCB_VIA))
info['tracks_per_layer']=dict(counts);info['vias']=sum(isinstance(t,k.PCB_VIA) for t in b.GetTracks());info['via_in_pad_locations']=len(mapped)
info['mounting_hole_centers_mm']={f.GetReference():xy(f.GetPosition()) for f in b.GetFootprints() if f.GetReference().startswith('H')}
info['native_drc']=json.loads((D/'drc.json').read_text(encoding='utf-8'))
info['native_drc']={key:len(info['native_drc'][key]) for key in ['violations','unconnected_items','schematic_parity']}
info['board_sha256']=hashlib.sha256((D/'analog_matrix_4x4.kicad_pcb').read_bytes()).hexdigest()
(D/'pcb_audit.json').write_text(json.dumps(info,indent=2));print({k:v for k,v in info.items() if k not in ['protected_inverting_nodes']})
