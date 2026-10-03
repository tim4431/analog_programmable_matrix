"""LC1 PCB placement and retained-routing seed. Run with KiCad's Python.
Sensitive paths are placed locally; final routing is checked by KiCad DRC.
"""
from pathlib import Path
import json, math
import pcbnew as k
ROOT=Path(__file__).resolve().parents[1]; REPO=ROOT.parents[1]
DEST=ROOT/'hardware'; BASE=REPO/'pcb/analog_matrix_4x4_rev_d'
manifest=json.loads((DEST/'design_instances.json').read_text())
parts={p['ref']:p for p in manifest['parts']}
b=k.LoadBoard(str(BASE/'analog_matrix_4x4.kicad_pcb'))
oldfps={f.GetReference():f for f in b.GetFootprints()}
oldpads={(f.GetReference(),p.GetNumber()):(tuple(p.GetPosition()),str(p.GetNetname())) for f in oldfps.values() for p in f.Pads()}
mm=lambda x:k.FromMM(x)
vec=lambda x,y:k.VECTOR2I(mm(x),mm(y))
nets={str(n.GetNetname()):n for n in b.GetNetsByNetcode().values()}
for p in parts.values():
 for net in p['pins'].values():
  if net and net not in nets:
   n=k.NETINFO_ITEM(b,net);b.Add(n);nets[net]=n
print('API types at start',type(b.Zones()),type(b.GetTracks()),flush=True)
# Keep external connectors, modules, output stages and original amplifier cells.
for ref,f in list(oldfps.items()):
 if ref not in parts and not ref.startswith('H'):b.Remove(f);f.thisown=False
fps={f.GetReference():f for f in b.GetFootprints()}
for ref,p in parts.items():
 if ref not in fps:
  f=k.FootprintLoad(str(DEST/'AnalogMatrix.pretty'),p['footprint'].split(':')[1]);assert f
  b.Add(f);f.SetReference(ref);f.SetFPIDAsString(p['footprint']);fps[ref]=f
 f=fps[ref];f.SetValue(p['value']);f.SetDNP(p['dnp']);f.SetExcludedFromBOM(False)
 path=k.KIID_PATH()
 for value in manifest['instances'][ref]['path'].strip('/').split('/'):path.push_back(k.KIID(value))
 f.SetPath(path);f.SetSheetfile(manifest['instances'][ref]['sheet']+'.kicad_sch')
 f.SetSheetname(manifest['instances'][ref]['sheet'])
 for pad in f.Pads():
  n=pad.GetNumber()
  if not n:continue
  assert n in p['pins'],(ref,n)
  net=p['pins'][n]
  pad.SetNet(nets[net] if net else nets[''])
 f.Value().SetVisible(False)
 f.Reference().SetTextSize(vec(.75,.75));f.Reference().SetTextThickness(mm(.12))
 f.Reference().SetVisible(True)

def pos(ref,x,y,angle=0):
 f=fps[ref];f.SetPosition(vec(x,y));f.SetOrientationDegrees(angle)
 f.Reference().SetTextAngle(k.EDA_ANGLE(0,k.DEGREES_T));f.Reference().SetPosition(vec(x,y-4 if ref.startswith('U') else y-1.7))
 return f

print('API types after footprints',type(b.Zones()),type(b.GetTracks()),flush=True)
k.SaveBoard(str(REPO/'.work/lc1/stage1.kicad_pcb'),b)
# Dual input buffers, matched polarity cells, and their local feedback parts.
for pair,y in enumerate([35,95]):
 pos('U'+str(200+pair),21,y)
 for n,off in [(1,-1.4),(2,1.4)]:
  ref=f'C{1+16*pair+(n-1)}';pos(ref,16.4 if n==2 else 25.7,y+off,90)
for i in range(4):
 y=20+30*i;pos(f'U{202+i}',36,y)
 # A: positive channel on the left; B: negative on the right.
 r=1+9*i
 pos(f'R{r+3}',27.8,y-2.4);pos(f'R{r+4}',30,y+1.0,90)
 pos(f'R{r+5}',30.4,y-3.8,90)  # left OUT/IN- feedback
 pos(f'R{r+6}',30.4,y-8.5,90)
 pos(f'R{r+7}',42.0,y+1.8,90)
 pos(f'R{r+8}',42.0,y-2.6,90)
 pos(f'C{3+8*i}',40.5,y-5,0);pos(f'C{4+8*i}',31.5,y+4.5,0)
# Matrix cells preserve the ADA4899 locations and 1 pF feedback placement.
for row in range(4):
 y=20+30*row
 pos(f'U{220+2*row}',53,y)
 pos(f'U{221+2*row}',97,y)
 for j,(x,dy,ang) in enumerate([(73,-7,90),(73,7,90),(77,7,270),(77,-7,270)]):
  pos(f'U{300+4*row+j}',x,y+dy,ang)
  pos(f'C{300+4*row+j}',x,y+dy+(-4.5 if dy<0 else 4.5),0)
 pos(f'C{63+34*row}',72,y,0);pos(f'C{64+34*row}',78,y,0)
 for ref,x in [(39+24*row,53),(51+24*row,97)]:pos(f'R{ref}',x,y-5,0)
 # Move the retained switch bypass caps to the dual supply pads.
 for old,new in [(40+4*row,220+2*row),(42+4*row,221+2*row)]:
  x=53 if old%4==0 else 97
  for p in parts.values():
   if p.get('old_ref')==f'C_U{old}_P':pos(p['ref'],x+5,y-1.6,90)
   if p.get('old_ref')==f'C_U{old}_N':pos(p['ref'],x-5,y+.9,90)
# Place two summers together per package and keep each resistor bank at its input.
for pair,y in enumerate([35,95]):
 pos(f'U{206+pair}',113,y)
 pos(f'U{228+pair}',124.3,y)
 for ch,row in enumerate([pair*2,pair*2+1]):
  rf=53+24*row
  x=107.6 if ch==0 else 118.4
  pos(f'R{rf}',x,y+(-1.27 if ch==0 else 1.27),90)
  # Reorient summing resistors towards the input bank; keep high impedance copper short.
  for j in range(4):
   pos(f'R{40+24*row+4*j}',102.8 if ch==0 else 113+4*(j%2),y-8.5+1.8*j if ch==0 else y-10+2*(j//2),0 if ch==0 else 180)
  pos(f'R{rf+1}',102.8 if ch==0 else 113,y+1 if ch==0 else y+4.8,0 if ch==0 else 180)
  pos(f'R{rf+2}',102.8 if ch==0 else 113,y+3.2 if ch==0 else y+7,0 if ch==0 else 180)
  pos(f'R{rf+3}',109 if ch==0 else 118.4,y-5.5 if ch==0 else y+5.5,90)
 for old,new in [(80+2*pair,206+pair),(84+2*pair,228+pair)]:
  x=113 if old<84 else 124.3
  for p in parts.values():
   if p.get('old_ref')==f'C_U{old}_P':pos(p['ref'],x+4.8,y-4,0)
   if p.get('old_ref')==f'C_U{old}_N':pos(p['ref'],x-4.8 if old<84 else x,y+4 if old<84 else y+5.5,0)
# DC trim island: its low-bandwidth outputs can travel to the row resistor banks.
pos('U400',82.5,139,0);pos('U401',98,139,0)
for i in range(4):
 left=i<2;y=134+10*(i%2);x=91.5 if left else 104.5
 pos(f'R{300+2*i}',x-3 if left else x+3,y,90)
 pos(f'R{301+2*i}',x,y,90)
 pos(f'C{320+i}',x+2 if left else x-2,y,90)
pos('C324',86.8,137,90);pos('C327',81.5,143,0)
pos('C325',92.8,139,90);pos('C326',103.2,139,90)
pos('R308',77.4,136.5,90);pos('R309',77.4,139.5,90)
print('API types after placement',type(b.Zones()),type(b.GetTracks()),flush=True)
k.SaveBoard(str(REPO/'.work/lc1/stage2.kicad_pcb'),b)
# Retain only nets whose connected pad positions did not change. Preserve GND
# thermal vias/planes; changed-region conflicts are removed in the DRC cleanup.
newpads={(f.GetReference(),p.GetNumber()):(tuple(p.GetPosition()),str(p.GetNetname())) for f in fps.values() for p in f.Pads()}
changed=set()
for key in set(oldpads)|set(newpads):
 if oldpads.get(key)!=newpads.get(key):
  for record in [oldpads.get(key),newpads.get(key)]:
   if record and record[1]:changed.add(record[1])
removed=0
for track in list(b.GetTracks()):
 if str(track.GetNetname()) in changed and str(track.GetNetname())!='GND':b.Remove(track);track.thisown=False;removed+=1
print('API types after track removal',type(b.Zones()),type(b.GetTracks()),flush=True)
k.SaveBoard(str(REPO/'.work/lc1/stage3.kicad_pcb'),b)
# Refresh ground-pour exclusions around only the currently sensitive pads.
for z in list(b.Zones()):
 if z.GetIsRuleArea():b.Remove(z);z.thisown=False
print('Zones cleared',flush=True)
for f in fps.values():
 for p in f.Pads():
  net=str(p.GetNetname())
  sensitive=net.startswith(('IOUT_','SN','PN','NN','DRVN'))
  if not sensitive:continue
  x,y=p.GetPosition();sx,sy=p.GetSize();
  for layer in [k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu]:
   z=k.ZONE(b);z.SetLayer(layer);z.SetIsRuleArea(True);z.SetDoNotAllowCopperPour(True)
   z.SetDoNotAllowTracks(False);z.SetDoNotAllowVias(False);z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False)
   z.Outline().NewOutline()
   for dx,dy in [(-sx/2-mm(.3),-sy/2-mm(.3)),(sx/2+mm(.3),-sy/2-mm(.3)),(sx/2+mm(.3),sy/2+mm(.3)),(-sx/2-mm(.3),sy/2+mm(.3))]:z.Outline().Append(int(x+dx),int(y+dy))
   b.Add(z)
print('Zones made',flush=True)
# Board text names the alternative revision, keeping the connector labels.
for item in b.GetDrawings():
 if isinstance(item,k.PCB_TEXT):
  t=item.GetText().replace('REV D','LC1').replace('REV_D','LC1').replace('PCB D','PCB LC1').replace('AD5544','DAC7811')
  item.SetText(t)
b.SetFileName(str(DEST/'analog_matrix_lc1.kicad_pcb'))
b.GetTitleBlock().SetRevision('LC1')
print('Saving board',flush=True)
b.BuildListOfNets();b.BuildConnectivity()
k.SaveBoard(str(DEST/'analog_matrix_lc1.kicad_pcb'),b)
print('Placed',len(parts),'parts; removed',removed,'changed-net track segments')
# Record placements for auditing and re-running the seed generator.
(DEST/'placements.json').write_text(json.dumps({r:[k.ToMM(f.GetPosition().x),k.ToMM(f.GetPosition().y),f.GetOrientationDegrees()] for r,f in fps.items()},indent=2))
