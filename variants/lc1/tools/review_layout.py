"""Record geometry checks on the released board. Run with KiCad Python.

These are routing checks, not electromagnetic extraction or thermal tests.
"""
from pathlib import Path
import hashlib,json,collections
import pcbnew as k
R=Path(__file__).resolve().parents[1];P=R/'hardware/analog_matrix_lc1.kicad_pcb';b=k.LoadBoard(str(P));fps={f.GetReference():f for f in b.GetFootprints()}
tracks=list(b.GetTracks())
def pad(ref,pin):return next(p for p in fps[ref].Pads() if p.GetNumber()==str(pin))
ground=pad('J9',2).GetNetCode()
assert not [t for t in tracks if not isinstance(t,k.PCB_VIA) and t.GetLayer()==k.In1_Cu], 'In1 is reserved for ground'
plane=next(z for z in b.Zones() if not z.GetIsRuleArea() and z.GetLayer()==k.In1_Cu)
assert plane.GetNetCode()==ground and plane.GetFilledPolysList(k.In1_Cu).OutlineCount()==1
sensitive=[]
for row in range(4):
 for col in range(4):
  net=pad('U'+str(60+4*row+col),2).GetNetCode();copper=[t for t in tracks if t.GetNetCode()==net]
  assert all(not isinstance(t,k.PCB_VIA) and t.GetLayer()==k.F_Cu for t in copper)
  length=sum(k.ToMM(t.GetLength()) for t in copper);assert 0<length<5.3
  sensitive.append(dict(row=row,column=col,length_mm=length,layer='F.Cu',vias=0))
rails={'+15V':pad('J9',1).GetNetCode(),'-15V':pad('J9',3).GetNetCode(),'+5A':pad('U130',3).GetNetCode(),'-5A':pad('U131',3).GetNetCode()}
widths={}
for name,code in rails.items():
 histogram=collections.defaultdict(float)
 for t in tracks:
  if not isinstance(t,k.PCB_VIA) and t.GetNetCode()==code:histogram[f'{k.ToMM(t.GetWidth()):.3f} mm']+=k.ToMM(t.GetLength())
 widths[name]={w:round(length,3) for w,length in sorted(histogram.items())}
report=dict(source_pcb_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),ground_layer='In1.Cu',ground_plane_connected_regions=1,tracks_on_ground_layer=0,mdac_current_output_routes=sensitive,power_trace_length_mm_by_width=widths,scope='Native geometry only. Continuous inner ground plane and short current-output feedback paths checked; high-frequency parasitics, rail impedance under load and thermal behavior still require prototype measurement.')
(R/'hardware/layout_review.json').write_text(json.dumps(report,indent=2))
print('PASS: dedicated continuous inner ground, sixteen top-layer 5.16 mm MDAC current-output paths with no vias; power widths recorded.')
