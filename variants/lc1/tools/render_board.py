"""Prepare actual KiCad layer artwork and a Blender render of the LC1 CAD.

Run with ordinary Python; KiCad CLI, Inkscape and Blender paths may be passed.
No generated artwork is substituted for electrical geometry.
"""
from pathlib import Path
import argparse, re, subprocess, xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--kicad',default=r'C:\Program Files\KiCad\8.0\bin\kicad-cli.exe')
parser.add_argument('--inkscape',default=r'C:\Program Files\Inkscape\bin\inkscape.exe')
parser.add_argument('--blender',default=r'C:\Program Files\Blender Foundation\Blender 4.3\blender.exe')
parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
D=ROOT/'mechanical';WORK=REPO/'.work/lc1/artwork';WORK.mkdir(parents=True,exist_ok=True)
P=ROOT/'hardware/analog_matrix_lc1.kicad_pcb';ns='http://www.w3.org/2000/svg';ET.register_namespace('',ns)
svg=ET.Element('{'+ns+'}svg',dict(version='1.1',width='160mm',height='170mm',viewBox='0 0 160 170'))
ET.SubElement(svg,'{'+ns+'}rect',dict(x='0',y='0',width='160',height='170',fill='#126342'))
for layer,name,color in [('F.Cu','copper','#1a6849'),('F.Mask','mask','#c9bda1'),('F.SilkS','silk','#e4ede2')]:
 path=WORK/(name+'.svg')
 subprocess.run([args.kicad,'pcb','export','svg','--layers',layer,'--black-and-white','--page-size-mode','1','--exclude-drawing-sheet','--drill-shape-opt','0','--output',str(path),str(P)],check=True)
 root=ET.fromstring(path.read_text().replace('#000000',color))
 for child in root:
  if child.tag.endswith('}g'):svg.append(child)
ET.ElementTree(svg).write(D/'pcb_surface.svg',encoding='utf-8',xml_declaration=True)
subprocess.run([args.inkscape,str(D/'pcb_surface.svg'),'--export-type=png','--export-width=2400','--export-filename='+str(D/'pcb_surface.png')],check=True)
source=(REPO/'mechanical/analog_matrix_package_m3/render_package.py').read_text()
source=source.replace("D=BASE if (BASE/'render_geometry.json').exists() else BASE/'analog_matrix_package_m3'","D=BASE")
source=source.replace("scene.cycles.samples=48","scene.cycles.samples=32")
source=source.replace("render('power_entry_assembled')","# Detail render omitted for this variant.")
source=source.replace("render('power_entry_detail')","# Detail render omitted for this variant.")
source=source.replace("text('ANALOG MATRIX'","text('ANALOG MATRIX LC1'")
(D/'render_package.py').write_text(source)
if not args.prepare_only:subprocess.run([args.blender,'--background','--python',str(D/'render_package.py')],check=True)
print('LC1 CAD render pipeline complete')
