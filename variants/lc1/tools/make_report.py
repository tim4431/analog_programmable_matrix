"""Build a compact review report from recorded, hash-checked simulation data."""
from pathlib import Path
import hashlib, json, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT

ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
sys.path.insert(0,str(REPO/'spice'))
from read_raw import read_raw
SIM=ROOT/'simulation';OUT=SIM/'report';OUT.mkdir(exist_ok=True)
results=json.loads((SIM/'results.json').read_text())
assert len(results)==35 and all(r['status']=='completed' and r['evidence_matches_netlist'] for r in results)
for r in results:
    assert hashlib.sha256((SIM/'benches'/r['bench']).read_bytes()).hexdigest()==r['sha256']
lookup={r['bench'].removesuffix('.cir'):r for r in results}
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.18})
def data(name):return read_raw(SIM/'benches'/(name+'.raw'))[1]

fig,ax=plt.subplots(figsize=(8,3.2))
for name,label in [('row_ac','Nominal, positive'),('row_ac_negative','Nominal, negative'),('row_ac_high_r','12 kohm / 20 pF corner'),('row_ac_bandwidth_stress','5 MHz DAC pole stress')]:
    v=data(name);ax.semilogx(v['frequency'].real,100*(abs(v['v(b0)']/v['v(b0)'][0])-1),label=label)
ax.set(xlim=(1e3,1e6),ylim=(-2.5,.1),xlabel='Frequency (Hz)',ylabel='Gain relative to DC (%)')
ax.axhline(-1,color='#ad453b',ls='--',lw=1);ax.legend(fontsize=8,loc='lower left');fig.tight_layout();fig.savefig(OUT/'gain.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(8,3.2));settling={}
for name,label in [('row_step','50 ohm + 20 pF'),('row_step_1nf','50 ohm + 1 nF')]:
    v=data(name);t=v['time'];out=v['v(b0)'];steady=lookup[name]['steady_voltage']
    window=(t>=1e-6)&(t<5e-6);tw=t[window];yw=out[window]
    bad=np.flatnonzero(abs(yw-steady)>.01*abs(steady))
    settling[name]=float((tw[bad[-1]+1]-1e-6)*1e9) if len(bad) and bad[-1]+1<len(tw) else None
    ax.plot(t*1e6,out,label=label)
ax.set(xlim=(.7,7),xlabel='Time (us)',ylabel='Loaded output (V)');ax.legend(fontsize=8);fig.tight_layout();fig.savefig(OUT/'step.png',dpi=180);plt.close(fig)
(OUT/'step_metrics.json').write_text(json.dumps(settling,indent=2))
loops=[r for r in results if r['bench'].startswith('loop')]
groups=[('Input buffers', 'loop_input_buffer'),('Positive drivers','loop_input_positive'),('Negative drivers','loop_input_negative'),('MDAC TIAs','loop_tia'),('Row summer','loop_summer'),('Output drivers','loop_driver'),('Offset trim','loop_trim')]
mins=[min(r['min_phase_margin_deg'] for r in loops if r['bench'].startswith(prefix)) for _,prefix in groups]
fig,ax=plt.subplots(figsize=(8,2.9));bars=ax.barh([a for a,b in groups],mins,color='#266b7e');ax.axvline(45,ls='--',color='#ad453b',lw=1)
for bar,val in zip(bars,mins):ax.text(val+.5,bar.get_y()+bar.get_height()/2,f'{val:.1f}',va='center',fontsize=9)
ax.set(xlim=(0,90),xlabel='Minimum modeled phase margin (degrees)');ax.invert_yaxis();fig.tight_layout();fig.savefig(OUT/'stability.png',dpi=180);plt.close(fig)

styles=getSampleStyleSheet()
styles['Normal'].fontSize=10;styles['Normal'].leading=14;styles['Normal'].spaceAfter=8
styles['Title'].fontSize=25;styles['Title'].leading=29;styles['Title'].alignment=TA_LEFT
styles['Heading1'].fontSize=17;styles['Heading1'].leading=21;styles['Heading1'].spaceAfter=12
styles['Heading2'].fontSize=12;styles['Heading2'].leading=16
story=[]
def p(s,style='Normal'):story.append(Paragraph(s,styles[style]))
def table(rows,widths):
    t=Table([[Paragraph(str(x),styles['Normal']) for x in row] for row in rows],colWidths=widths,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e7f0f2')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#266b7e')),('BOTTOMPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5)]));story.append(t);story.append(Spacer(1,10))
def img(name,height):story.append(Image(str(OUT/name),width=500,height=height));story.append(Spacer(1,8))
p('Analog matrix LC1','Title');p('Circuit simulation review | 2 October 2026')
p('A separate 12-bit, lower-cost alternative to Revision D. Both designs are unbuilt prototypes. This report covers the circuit model; PCB design-rule evidence is supplied separately.')
table([['Target','LC1 implementation'],['Signal path','4 inputs x 4 outputs; signed coefficients; DC through 1 MHz'],['Amplitude / load','Inputs +/-1 V peak; outputs +/-4 V peak into external 50 ohm. Internal driver swing approaches +/-8 V.'],['Coefficient control','16 DAC7811 multiplying DACs, eight OPA2810 duals, ten TMUX6136 dual switches; original ADA4899 TIAs and THS3091 output drivers retained.'],['Offset correction','MCP4728 + OPA4197; 100 us analog filters; 2 ms muted settling interval.']], [108,392])
p('What the results establish','Heading2')
p('35 recorded benches completed: 13 row transfer/large-signal cases and 22 feedback-loop cases. Netlist SHA-256 values match the recorded results. Nominal magnitude droop at 1 MHz is 0.70%; the modeled resistor/capacitance corner reaches 0.86%. Minimum modeled phase margin is 57.5 degrees. Firmware protocol and failure-muting tests pass on a host simulator.')
p('What remains to be measured','Heading2')
p('The DAC is represented by a datasheet-derived current-output network plus an assumed 10 MHz first-order pole. TI\'s available DAC7811 model is encrypted and was not used in LTspice. Switches use static resistance/capacitance models. Thus these results do not guarantee 1% accuracy, cancellation depth, crosstalk, switching glitches, noise, temperature drift or stability on the finished PCB.')
p('An intentionally slower 5 MHz DAC-pole stress gives 2.15% droop at 1 MHz and misses the target. The datasheet bandwidth is typical, not a guaranteed lower limit. Qualify actual assembled boards over frequency and temperature; keep the original design available until that comparison is complete.')
story.append(PageBreak())
p('Transfer response and settling','Heading1')
img('gain.png',200)
p('Each curve is normalized to its own DC gain, as after gain calibration. The nominal full-scale coefficient uses q=0.93552 to allow calibration headroom. The resistor/capacitance corner uses 12 kohm DAC resistance, 20 pF total summing-node capacitance, 1.5 pF total feedback capacitance, and 245 ohm switch resistance.')
img('step.png',200)
p(f'All four inputs step from 0 to +1 V together and return to zero. The nominal output settles to 3.9945 V (uncorrected modeled DC offset included). The recorded 1% rise settling times are {settling["row_step"]:.0f} ns with 20 pF and {settling["row_step_1nf"]:.0f} ns with 1 nF. Both transient runs reach 12 us; no sustained ringing is present in these models.')
p('DC sweeps cover both input polarities and both coefficient signs. The fitted slope is within 0.001% of unity in the ideal calibrated model; the largest fitted residual is below 1.6 uV. This is a model result, not a tolerance or measurement claim. The typical modeled untrimmed output offset is about -5.5 mV.')
story.append(PageBreak())
p('Feedback stability and design limits','Heading1')
img('stability.png',182)
p('Loop gain is measured with an AC series injection while retaining the DC operating point. Phase margins are evaluated at downward unity-gain crossings. The input loops include all four reference loads. Twelve TIA cases cover 8/10/12 kohm feedback resistance, 10/20 pF input capacitance, and 1.1/1.5 pF total feedback capacitance. Output-driver cases include 20 pF and 1 nF loads behind the 49.9 ohm source resistor.')
p('Use 1.0 pF C0G +/-0.1 pF TIA compensation capacitors and short feedback paths. Do not substitute a slower amplifier or change a current-feedback driver\'s feedback resistor without repeating the analysis. Plane exclusions around sensitive summing pads reduce capacitance; final parasitics require hardware checks.')
p('Accuracy and calibration','Heading2')
p('Twelve-bit coefficient magnitude gives approximately 0.026% coefficient steps after the analog gain reserve. Calibrate the positive and negative gain of every coefficient separately with the actual 50 ohm measurement load. Trim each output at zero input; the nominal trim step is about 55 uV at the loaded connector. Small-coefficient relative error is not a guaranteed specification.')
p('Bench qualification','Heading2')
p('Start muted with current-limited analog rails, no input signal, and installed insulated regulator heatsinks. Check all rails and offsets, then calibrate DC gain and offset. Sweep each matrix path through 1 MHz, check all-positive/all-negative sums at full amplitude, inspect output and internal amplifier nodes for oscillation, and run a full-load thermal soak inside the enclosure. Check power sequencing and cable loading. USB and analog grounds are common.')
p('Reproduction and primary references','Heading2')
p('LTspice 24.1.3; vendor amplifier macromodels plus documented behavioral DAC/switch elements. Transients use Gear integration. Sources, checksums, benches, results and the report generator are stored alongside this PDF. Vendor models are downloaded separately subject to their licenses.')
p('Manufacturer datasheets: '+ ' | '.join(f'<link href="{url}" color="#266b7e">{label}</link>' for label,url in [('DAC7811','https://www.ti.com/lit/ds/symlink/dac7811.pdf'),('OPA2810','https://www.ti.com/lit/ds/symlink/opa2810.pdf'),('TMUX6136','https://www.ti.com/lit/ds/symlink/tmux6136.pdf'),('OPA4197 family','https://www.ti.com/lit/ds/symlink/opa197.pdf'),('MCP4728','https://ww1.microchip.com/downloads/en/DeviceDoc/22187E.pdf')]))
def footer(c,doc):
    c.setFont('Helvetica',8);c.setFillColor(colors.HexColor('#65737b'));c.drawString(47,28,'LC1 | Simulation evidence, not measured hardware specifications');c.drawRightString(548,28,str(doc.page))
SimpleDocTemplate(str(OUT/'LC1_simulation_review.pdf'),pagesize=(595.28,841.89),leftMargin=47,rightMargin=48,topMargin=42,bottomMargin=43,title='Analog matrix LC1 simulation review',author='Analog Programmable Matrix').build(story,onFirstPage=footer,onLaterPages=footer)
print(json.dumps({'benches':len(results),'minimum_phase_margin':min(mins),'settling_ns':settling,'pdf':str(OUT/'LC1_simulation_review.pdf')},indent=2))
