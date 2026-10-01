"""Render actual KiCad plot geometry as a readable bare-board top view."""
from pathlib import Path
import subprocess,xml.etree.ElementTree as ET,re,copy,pcbnew as k
R=Path(__file__).resolve().parent.parent;D=R/'pcb/analog_matrix_4x4_rev_d';W=R/'pcb/work_d';CLI=r'C:\Program Files\KiCad\8.0\bin\kicad-cli.exe'
W.mkdir(parents=True,exist_ok=True)
layers=['F.Cu','F.Mask','F.Silkscreen','Edge.Cuts'];roots=[]
for layer in layers:
    out=W/('preview_'+layer.replace('.','_')+'.svg')
    subprocess.run([CLI,'pcb','export','svg','--layers',layer,'--page-size-mode','2','--exclude-drawing-sheet','--output',str(out),str(D/'analog_matrix_4x4.kicad_pcb')],capture_output=True,check=True)
    roots.append(ET.parse(out).getroot())
NS='http://www.w3.org/2000/svg';ET.register_namespace('',NS)
root=ET.Element('{'+NS+'}svg',roots[0].attrib)
ET.SubElement(root,'{'+NS+'}title').text='Analog matrix PCB D - actual top copper, solder-mask openings and silkscreen'
ET.SubElement(root,'{'+NS+'}rect',{'x':'0','y':'0','width':'100%','height':'100%','fill':'#0c3027'})
colors=['#1d5643','#d7bd7e','#f5f1df','#b4c3ad']
for source,color in zip(roots,colors):
    for elem in list(source):
        if elem.tag.endswith('title') or elem.tag.endswith('desc'):continue
        text=ET.tostring(elem,encoding='unicode')
        # Plot colors are presentation only; all path coordinates stay native.
        text=re.sub(r'#[0-9a-fA-F]{6}',lambda m:'#071a15' if m.group().upper()=='#FFFFFF' else color,text)
        if color=='#d7bd7e':text=re.sub(r'fill-opacity:[0-9.]+','fill-opacity:1',text)
        root.append(ET.fromstring(text))
board=k.LoadBoard(str(D/'analog_matrix_4x4.kicad_pcb'))
for f in board.GetFootprints():
    for p in f.Pads():
        diameter=k.ToMM(p.GetDrillSize().x)
        # The specified small filled/capped thermal vias have no open hole.
        if diameter<=.2:continue
        pos=p.GetPosition();ET.SubElement(root,'{'+NS+'}circle',{'cx':str(k.ToMM(pos.x)+.025),'cy':str(k.ToMM(pos.y)+.025),'r':str(diameter/2),'fill':'#061a15'})
out=D/'pcb_top_view.svg';ET.ElementTree(root).write(out,encoding='utf-8',xml_declaration=True)
subprocess.run([r'C:\Program Files\Inkscape\bin\inkscape.com',str(out),'--export-type=png','--export-filename='+str(D/'pcb_top_view.png'),'--export-width=1800'],capture_output=True,check=True)
print(D/'pcb_top_view.png')
