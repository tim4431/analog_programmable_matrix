"""Dimensioned clearance explanation based on the M3 CAD review."""
from pathlib import Path
import json,html,subprocess
D=Path(__file__).resolve().parent
r=json.loads((D/'bnc_access_checks.json').read_text())
assert not r['collisions']
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="720" viewBox="0 0 1200 720">',
 '<rect width="1200" height="720" fill="#f7f9fb"/>',
 '<style>text{font-family:Arial,sans-serif;fill:#223746} .small{font-size:16px}</style>',
 '<defs><marker id="arrow" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto-start-reverse"><path d="M0,0 L6,3 L0,6" fill="none" stroke="#466474"/></marker></defs>']
def text(x,y,t,size=18,anchor='start',color='#223746'):
 svg.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" fill="{color}">{html.escape(t)}</text>')
def line(x1,y1,x2,y2,color='#466474',dash=''):
 svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.5" stroke-dasharray="{dash}"/>')
def dim(x,y1,y2,label):
 svg.append(f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" stroke="#466474" marker-start="url(#arrow)" marker-end="url(#arrow)"/>')
 text(x+14,(y1+y2)/2+6,label,18)
text(44,52,'BNC CABLE ACCESS / PCB D + ENCLOSURE M3',29)
text(44,83,'Nominal CAD check with all eight straight plugs attached',19)
svg.append('<rect x="90" y="126" width="460" height="104" rx="4" fill="#647c89"/>')
text(320,183,'RAISED POWER HOOD',20,'middle','#ffffff')
sc=8;cx=310;rear=230+12.3*sc;front=rear+30*sc
for y,label in [(rear,'b3'),(front,'b2')]:
 svg.append(f'<circle cx="{cx}" cy="{y}" r="72" fill="#dfe7eb" stroke="#64818f" stroke-width="1.5"/>')
 svg.append(f'<circle cx="{cx}" cy="{y}" r="68" fill="#fff2d5" stroke="#b67b25" stroke-width="2"/>')
 svg.append(f'<circle cx="{cx}" cy="{y}" r="58" fill="#c8e8dc" stroke="#367d64" stroke-width="1.5"/>')
 text(cx,y+6,label,22,'middle')
 line(cx-8,y,cx+8,y);line(cx,y-8,cx,y+8)
line(154,rear,232,rear);line(154,front,232,front);dim(155,rear,front,'30 mm')
line(383,rear-68,482,rear-68);line(550,230,482,230);dim(482,230,rear-68,'3.8 mm')
line(383,rear+68,474,rear+68);line(383,front-68,474,front-68);dim(465,rear+68,front-68,'13 mm')
text(320,677,'TOP VIEW: closest pair; a3 / a2 have the same spacing',16,'middle')
text(626,162,'Collar and aperture',23)
for y,fill,stroke,label in [(203,'#c8e8dc','#367d64','14.5 mm typical collar'),(245,'#fff2d5','#b67b25','17 mm checked maximum envelope'),(287,'#dfe7eb','#64818f','18 mm opening through the cover')]:
 svg.append(f'<circle cx="640" cy="{y-5}" r="8" fill="{fill}" stroke="{stroke}"/>');text(661,y,label,19)
text(626,342,'With a typical 14.5 mm straight plug:',20)
text(642,377,'15.5 mm between adjacent collars',19)
text(642,410,'5.05 mm from rear collar to hood',19)
text(642,443,'1.75 mm radial margin in the opening',19)
text(626,496,'Use a side grip on a3 and b3.',22)
text(626,530,'Rear finger access is restricted; regrip if needed.',18)
text(626,563,'Plug rotation fits inside the circular envelope.',18)
text(626,603,'Straight plugs only; bulky boots, tees and elbows',17)
text(626,627,'need their own fit check. Confirm on the prototype.',17)
text(626,679,'Reference: Amphenol 31-320-RFX, catalog p108.',15)
svg.append('</svg>');(D/'bnc_clearances.svg').write_text('\n'.join(svg))
subprocess.run([r'C:\Program Files\Inkscape\bin\inkscape.com',str(D/'bnc_clearances.svg'),'--export-type=png','--export-filename='+str(D/'bnc_clearances.png')],check=True,capture_output=True)
notes='''BNC CABLE ACCESS REVIEW - PCB D / ENCLOSURE M3

RESULT
All eight straight BNC plug envelopes pass the nominal CAD insertion and
rotation clearance check. No PCB or enclosure geometry was changed.
The tightest ports are a3 (J4) and b3 (J8), adjacent to the raised hood.

DIMENSIONS
Connector pitch: 30 mm. Cover aperture: 18 mm diameter.
Jack mouth: 8.22 mm above the cover.
Typical reference collar: 14.5 mm diameter (Amphenol 31-320-RFX, p108).
With that collar: 15.5 mm plug-to-plug gap, 5.05 mm rear hood gap,
1.75 mm nominal radial clearance in the cover opening.
With the larger 17 mm check envelope: 13 mm plug-to-plug gap,
3.8 mm rear hood gap, and 0.5 mm radial opening clearance.

METHOD
Eight 17 mm diameter cylinders extend from 10 mm below the jack mouth
through a 100 mm vertical insertion/withdrawal sweep. All case solids,
and simultaneous neighboring plug envelopes were checked.
A rotationally symmetric collar retains the same envelope during locking.
The 10 mm overlap is a conservative working assumption, not a vendor mated
CAD measurement; verify mating depth against the actual cable and jack.

HAND ACCESS
There is limited room behind the rear collars. Grip them from the sides.
An illustrative two-finger screen (10 mm diameter x 20 mm tall fingertips,
0.5 mm collar gap, fingertips 1 mm above the cover) clears in two 45-degree
twists with regripping. A continuous 90-degree sweep of the same rigid
finger model intersects the hood at a3 and b3. This is a usability warning,
not a claim that a real hand cannot perform the turn in one movement.
No anthropometric assessment or physical hand trial has been performed.

ASSEMBLY LIMITS
The 17 mm case has only 0.5 mm radial margin before printing/alignment
tolerances; use standard 14-15 mm collars where practical. Measure actual
printed holes and connector alignment. Large moulded boots, BNC tees and
right-angle plugs are not qualified by this check. Let cables rise or
leave toward the open sides; observe the selected cable's minimum bend
radius instead of forcing a bend against the hood.

FILES
bnc_access_checks.json: measured nominal clearances and collision results.
bnc_clearances.png / .svg: dimensioned explanation.
check_access.py: reproducible CadQuery check of the released M3 solids.

SOURCE
Amphenol BNC catalog, p108 (31-320-RFX: 14.5 mm diameter, 29.8 mm length)
https://www.farnell.com/datasheets/1942962.pdf
'''
(D/'BNC_ACCESS_REVIEW.txt').write_text(notes)
print('Clearance drawing and review written.')
