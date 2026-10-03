"""Import a reviewed router session, restore names/models and refill planes.

Run in KiCad Python. Always run native DRC with schematic parity afterward.
This does not suppress violations or make a fabrication-readiness claim.
"""
from pathlib import Path
import argparse, json, xml.etree.ElementTree as ET
import pcbnew as k
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
P=ROOT/'hardware/analog_matrix_lc1.kicad_pcb'
args=argparse.ArgumentParser();args.add_argument('--session');opts=args.parse_args()
b=k.LoadBoard(str(P))
if opts.session:
 assert k.ImportSpecctraSES(b,str(Path(opts.session).resolve())), 'SES import failed'
fps={f.GetReference():f for f in b.GetFootprints()}
# KiCad assigns generated names to unlabeled nets. Match by complete pad set,
# not by names or apparent proximity, before renaming the routed board's nets.
xml=ET.parse(ROOT/'hardware/validation_netlist.xml').getroot()
schematic={}
for net in xml.findall('./nets/net'):
 name=net.get('name')
 for node in net.findall('node'):schematic[(node.get('ref'),node.get('pin'))]=name
renames={}
for ref,f in fps.items():
 for pad in f.Pads():
  key=(ref,pad.GetNumber())
  if key not in schematic:continue
  name=schematic[key];code=pad.GetNetCode()
  if code==0:
   assert name.startswith('unconnected-'),(ref,pad.GetNumber(),'Connected schematic pin has no PCB net')
   net=k.NETINFO_ITEM(b,name);b.Add(net);pad.SetNet(net);continue
  if code in renames:assert renames[code]==name,(ref,pad.GetNumber(),'PCB net joins distinct schematic nets')
  else:renames[code]=name
assert len(set(renames.values()))==len(renames), 'Schematic net is split across PCB net codes'
for code,name in renames.items():b.FindNet(code).SetNetname(name)
model_names={'ADA4899_RD8_EP2.29x2.29':'ADA4899_RD8_EP2.29x2.29.step',
 'Pico_2x20_Socket_17.78mm':'Pico_2x20_Socket_17.78mm.step',
 'TO-220-3_Vertical':'TO-220-3_Vertical_Trimmed.step',
 'SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.95x4.9mm_Mask2.71x3.4mm_ThermalVias':'SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.95x4.9mm_Mask2.71x3.4mm.step'}
for f in fps.values():
 name=model_names.get(str(f.GetFPID().GetLibItemName()))
 if name:
  f.Models().clear();model=k.FP_3DMODEL();model.m_Filename='${KIPRJMOD}/../../../mechanical/analog_matrix_package_m3/models/'+name;f.Add3DModel(model)
b.GetTitleBlock().SetDate('2026-10-02')
b.GetTitleBlock().SetComment(0,'LC1: 12-bit prototype | +/-1 V in | +/-4 V into 50 ohms')
for item in b.GetDrawings():
 if isinstance(item,k.PCB_TEXT):item.SetText(item.GetText().replace('PCB D','PCB LC1'))
b.BuildListOfNets();b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(P),b)
print('Saved imported/refilled board; renamed',len(renames),'nets by pad membership')
