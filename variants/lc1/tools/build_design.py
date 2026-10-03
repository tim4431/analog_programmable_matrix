"""Build LC1 schematic from the preserved D signal-path drawings.

The original project is an immutable input. All new pin maps are explicit.
"""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import re
import shutil
import uuid
from sexpr import Quoted as Q, parse, dumps, get, items, prop, replace

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
BASE = REPO / 'pcb/analog_matrix_4x4_rev_d'
DEST = ROOT / 'hardware'
PROJECT = 'analog_matrix_lc1'
NS = uuid.UUID('c99c6b30-a42d-4eb2-a61f-b30eb2a25e14')
uid = lambda s: str(uuid.uuid5(NS, s))
data = json.loads((BASE / 'design_instances.json').read_text())
parts = {p['ref']: deepcopy(p) for p in data['parts']}
original = deepcopy(parts)
library = parse((BASE / 'AnalogMatrix.kicad_sym').read_text())
libs = {x[1]: deepcopy(x) for x in items(library, 'symbol')}
plans = {}
deleted = set()
sheet_ids = {}
root_id = uid('root')
old_root = get(parse((BASE / 'analog_matrix_4x4.kicad_sch').read_text()), 'uuid')[1]
base_sheet_ids={str(prop(s,'Sheetfile')[2]).removesuffix('.kicad_sch'):str(get(s,'uuid')[1])
                for s in items(parse((BASE/'analog_matrix_4x4.kicad_sch').read_text()),'sheet')}


def pin_number(pin):
    return str(get(pin, 'number')[1])


def unit(lib, number):
    return next(x for x in items(libs[lib], 'symbol') if x[1].endswith(f'_{number}_1'))


def footprint(name):
    return 'AnalogMatrix:' + name


def make_part(ref, value, pins, fp, old_ref=None, rating='', note=''):
    p = dict(ref=ref, value=value, pins={str(k): v for k, v in pins.items()},
             footprint=footprint(fp), package=fp, old_ref=old_ref or ref,
             rating=rating, note=note, dnp=False, polarized=False)
    parts[ref] = p
    return p


def drop(ref):
    deleted.add(ref)
    parts.pop(ref, None)


def derive_multi(name, base, channels, maps, power_map, desc, url):
    node = deepcopy(libs[base])
    node[1] = Q(name)
    prop(node, 'Value')[2] = Q(name)
    prop(node, 'Description')[2] = Q(desc)
    prop(node, 'Datasheet')[2] = Q(url)
    node[:] = [x for x in node if not (isinstance(x, list) and x[0] == 'symbol')]
    for i in range(channels):
        u = deepcopy(unit(base, 1)); u[1] = Q(f'{name}_{i+1}_1')
        u[:] = [x for x in u if not (isinstance(x, list) and x[0] == 'pin' and pin_number(x) not in maps[i])]
        for p in items(u, 'pin'):
            get(p, 'number')[1] = Q(str(maps[i][pin_number(p)]))
        node.append(u)
    u = deepcopy(unit(base, 2)); u[1] = Q(f'{name}_{channels+1}_1')
    u[:] = [x for x in u if not (isinstance(x, list) and x[0] == 'pin' and pin_number(x) not in power_map)]
    for p in items(u, 'pin'):
        get(p, 'number')[1] = Q(str(power_map[pin_number(p)]))
    node.append(u)
    libs[name] = node


opmaps = [{'3': '3', '2': '2', '6': '1'}, {'3': '5', '2': '6', '6': '7'}]
derive_multi('OPA2810IDR', 'OPA810ID', 2, opmaps, {'7': '8', '4': '4'},
             'Dual FET-input wideband amplifier', 'https://www.ti.com/lit/ds/symlink/opa2810.pdf')
swmaps = [{'2': '2', '8': '4', '1': '3', '6': '1'},
          {'2': '10', '8': '12', '1': '11', '6': '9'}]
derive_multi('TMUX6136PWR', 'TMUX6219DGKR', 2, swmaps, {'4': '13', '7': '5', '3': '6'},
             'Dual low-capacitance SPDT, powered from +/-15 V',
             'https://www.ti.com/lit/ds/symlink/tmux6136.pdf')
# Include package NC pads on the power unit, with explicit no-connect markers.
for idx, n in enumerate(['7', '8', '14', '15', '16']):
    unit('TMUX6136PWR', 3).append(parse(f'(pin passive line (at {-10.16+idx*5.08} -17.78 90) (length 5.08) (name "NC" (effects (font (size .8 .8)))) (number "{n}" (effects (font (size .8 .8)))))'))

quadmaps = [{'3': '3', '2': '2', '6': '1'}, {'3': '5', '2': '6', '6': '7'},
            {'3': '10', '2': '9', '6': '8'}, {'3': '12', '2': '13', '6': '14'}]
derive_multi('OPA4197IPWR', 'OPA197ID', 4, quadmaps, {'7': '4', '4': '11'},
             'Quad precision offset-trim amplifier', 'https://www.ti.com/lit/ds/symlink/opa197.pdf')


def merge(refs, newref, newlib, maps, fp, power_map, supplies=('+5A', '-5A')):
    pins = {}
    for i, oldref in enumerate(refs):
        old = original[oldref]
        for a, b in maps[i].items():
            pins[b] = old['pins'][a]
        plans[oldref] = dict(ref=newref, lib=newlib, analog=(i+1, maps[i]),
                             power=(len(refs)+1, power_map) if i == 0 else None)
        drop(oldref)
        if i:
            for p in original.values():
                if p['old_ref'] in (f'C_{oldref}_P', f'C_{oldref}_N', f'CB_{oldref}_P', f'CB_{oldref}_N'):
                    drop(p['ref'])
    for a, b in power_map.items():
        net = original[refs[0]]['pins'][a]
        pins[b] = supplies[0] if net == '+5A' else supplies[1] if net == '-5A' else net
    if newlib == 'TMUX6136PWR':
        pins.update({n: None for n in ['7','8','14','15','16']})
    make_part(newref, newlib, pins, fp, note='LC1 consolidation; not pin-compatible with Revision D')
    if supplies != ('+5A', '-5A'):
        for p in parts.values():
            if p['old_ref'] == f'C_{refs[0]}_P':
                p['pins']['1'] = supplies[0]
            if p['old_ref'] == f'C_{refs[0]}_N':
                p['pins']['1'] = supplies[1]


# Twelve input channels and four summing channels in eight dual packages.
for refs, newref in [(['U1','U4'],'U200'), (['U7','U10'],'U201'),
                     (['U2','U3'],'U202'), (['U5','U6'],'U203'),
                     (['U8','U9'],'U204'), (['U11','U12'],'U205'),
                     (['U80','U81'],'U206'), (['U82','U83'],'U207')]:
    merge(refs, newref, 'OPA2810IDR', opmaps, 'SOIC-8_3.9x4.9mm_P1.27mm', {'7':'8','4':'4'})
for i in range(8):
    merge([f'U{40+2*i}', f'U{41+2*i}'], f'U{220+i}', 'TMUX6136PWR', swmaps,
          'TSSOP-16_4.4x5mm_P0.65mm', {'4':'13','7':'5','3':'6'}, ('+15V','-15V'))
for i in range(2):
    merge([f'U{84+2*i}', f'U{85+2*i}'], f'U{228+i}', 'TMUX6136PWR', swmaps,
          'TSSOP-16_4.4x5mm_P0.65mm', {'4':'13','7':'5','3':'6'}, ('+15V','-15V'))


def box_symbol(name, units, desc, url):
    lib = parse(f'''(symbol "{name}" (pin_names (offset .508)) (in_bom yes) (on_board yes)
      (property "Reference" "U" (at 0 15.24 0) (effects (font (size 1 1))))
      (property "Value" "{name}" (at 0 12.7 0) (effects (font (size 1 1))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))
      (property "Datasheet" "{url}" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))
      (property "Description" "{desc}" (at 0 0 0) (effects (font (size 1 1)) (hide yes))))''')
    for i, (rect, pinspecs) in enumerate(units, 1):
        x1,y1,x2,y2 = rect
        u = parse(f'(symbol "{name}_{i}_1" (rectangle (start {x1} {y1}) (end {x2} {y2}) (stroke (width .254) (type default)) (fill (type background))))')
        for number, label, x, y, angle, typ in pinspecs:
            u.append(parse(f'(pin {typ} line (at {x} {y} {angle}) (length 5.08) (name "{label}" (effects (font (size .95 .95)))) (number "{number}" (effects (font (size .8 .8)))))'))
        lib.append(u)
    libs[name] = lib


box_symbol('DAC7811IDGSR', [((-10.16,10.16,10.16,-10.16), [
    (9,'VREF',-15.24,0,0,'passive'),(1,'IOUT1',15.24,0,180,'passive'),
    (10,'RFB',15.24,7.62,180,'passive'),(2,'IOUT2',0,-15.24,90,'power_in')]),
    ((-12.7,12.7,12.7,-12.7),[(4,'SCLK',-17.78,7.62,0,'input'),
     (5,'SDIN',-17.78,0,0,'input'),(6,'SYNC',-17.78,-7.62,0,'input'),
     (7,'SDO',17.78,0,180,'output'),(8,'VDD',0,17.78,270,'power_in'),
     (3,'GND',0,-17.78,90,'power_in')])],
    '12-bit multiplying DAC, 5 V supply, SPI mode 1, row daisy chain',
    'https://www.ti.com/lit/ds/symlink/dac7811.pdf')

for row in range(4):
    oldref = f'U{20+row}'
    old = original[oldref]
    units = {}
    for j, (ag, io, vr, fb) in enumerate([(1,2,3,4),(14,13,12,11),(15,16,17,18),(28,27,26,25)]):
        ref = f'U{300+4*row+j}'
        pm = {str(ag):'2',str(io):'1',str(vr):'9',str(fb):'10'}
        pins = {b:old['pins'][a] for a,b in pm.items()}
        pins.update({'3':'GND','4':'SCK','5':'MOSI' if j==0 else f'DAC_CHAIN_{row}_{j-1}',
                     '6':f'ROW{row}_CS','7':f'DAC_CHAIN_{row}_{j}' if j<3 else None,'8':'+5A'})
        make_part(ref,'DAC7811IDGSR',pins,'VSSOP-10_3x3mm_P0.5mm')
        units[j+1] = dict(ref=ref,lib='DAC7811IDGSR',unit=1,pinmap=pm)
        make_part(f'C{300+4*row+j}','100 nF',{'1':'+5A','2':'GND'},'C_0603_1608Metric',rating='25V X7R')
    plans[oldref] = dict(dacunits=units)
    drop(oldref)
    for p in original.values():
        if p['old_ref'] in (f'C_{oldref}_N',f'CB_{oldref}_N'):
            drop(p['ref'])

# The small coefficient stages retain their individually matched RFB resistors.
for row in range(4):
    parts[f'R{53+24*row}']['value']='549 ohm'
for p in parts.values():
    if p['value'].startswith('2.2 pF'):
        p['value']='1.0 pF C0G'
        p['rating']='50V C0G, +/-0.1pF; stray capacitance included in simulation'

# Rebuild the complete trim sheet around a slow quad voltage DAC.
old_trim_refs = {p['ref'] for p in data['placements'] if p['sheet']=='offset_trim'}
for ref in old_trim_refs:
    drop(ref)
for ref in ['R138','R139','R144','R145']:
    if ref in parts and any(n in ('LDAC_N','RESET_N','SIGNAL_EN','TRIM_CS') for n in parts[ref]['pins'].values()):
        drop(ref)
for ref, p in list(parts.items()):
    if ref.startswith('R') and any(n in ('LDAC_N','RESET_N','SIGNAL_EN','TRIM_CS') for n in p['pins'].values()):
        drop(ref)
for pin in ['11','12','17','20']:
    parts['U120']['pins'][pin]=None
parts['U120']['pins']['1']='TRIM_SDA'
parts['U120']['pins']['2']='TRIM_SCL'

box_symbol('MCP4728T-E_UN', [((-15.24,22.86,15.24,-22.86),[
    (1,'VDD',0,27.94,270,'power_in'),(2,'SCL',-20.32,12.7,0,'input'),
    (3,'SDA',-20.32,5.08,0,'bidirectional'),(4,'LDAC',-20.32,-2.54,0,'input'),
    (5,'RDY',-20.32,-10.16,0,'open_collector'),(6,'OUT A',20.32,15.24,180,'output'),
    (7,'OUT B',20.32,5.08,180,'output'),(8,'OUT C',20.32,-5.08,180,'output'),
    (9,'OUT D',20.32,-15.24,180,'output'),(10,'VSS',0,-27.94,90,'power_in')])],
    'Quad DC offset DAC; internal 2.048 V reference; gain 1',
    'https://ww1.microchip.com/downloads/en/DeviceDoc/22187E.pdf')
make_part('U400','MCP4728T-E_UN',{'1':'3V3','2':'TRIM_SCL','3':'TRIM_SDA','4':'GND','5':None,
          '6':'TRIM_RAW0','7':'TRIM_RAW1','8':'TRIM_RAW2','9':'TRIM_RAW3','10':'GND'},'MSOP-10_3x3mm_P0.5mm')
qp={'4':'+5A','11':'-5A'}
for i, pm in enumerate(quadmaps):
    qp[pm['3']]='GND';qp[pm['2']]=f'TN{i}';qp[pm['6']]=f'VTRIM{i}'
make_part('U401','OPA4197IPWR',qp,'TSSOP-14_4.4x5mm_P0.65mm')
for i in range(4):
    make_part(f'R{300+2*i}','10.0 k',{'1':f'TRIM_RAW{i}','2':f'TN{i}'},'R_0603_1608Metric',rating='0.1%, 25ppm/C')
    make_part(f'R{301+2*i}','10.0 k',{'1':f'VTRIM{i}','2':f'TN{i}'},'R_0603_1608Metric',rating='0.1%, 25ppm/C')
    make_part(f'C{320+i}','10 nF',{'1':f'VTRIM{i}','2':f'TN{i}'},'C_0603_1608Metric',rating='25V X7R; trim filter only')
for ref, value, net in [('C324','100 nF','3V3'),('C325','100 nF','+5A'),('C326','100 nF','-5A'),('C327','1 uF','3V3')]:
    make_part(ref,value,{'1':net,'2':'GND'},'C_0603_1608Metric',rating='25V X7R')
for ref, net in [('R308','TRIM_SDA'),('R309','TRIM_SCL')]:
    make_part(ref,'4.70 k',{'1':'3V3','2':net},'R_0603_1608Metric',rating='1%, 0.1W')
# Retain the original precision 2.5 V bias source and its local capacitors.
for ref in ['U110','C187','C188','C189','C190']:
    if ref in original and ref in old_trim_refs:
        parts[ref]=deepcopy(original[ref]);deleted.discard(ref)


def xy(node):
    at=get(node,'at')
    return (round(float(at[1]),4),round(float(at[2]),4)) if at else None


def ports(symbol, lib=None, un=None):
    lib=lib or get(symbol,'lib_id')[1].split(':',1)[1]
    un=un or int(get(symbol,'unit')[1])
    x,y=xy(symbol)
    assert float(get(symbol,'at')[3])==0
    return {pin_number(p):(round(x+float(get(p,'at')[1]),4),round(y-float(get(p,'at')[2]),4))
            for p in items(unit(lib,un),'pin')}


def uuid_walk(node):
    if not isinstance(node,list):return
    if node and node[0]=='uuid':node[1]=Q(uid(str(node[1])))
    for x in node:uuid_walk(x)


def label(net, pos, angle=0):
    x,y=pos
    return parse(f'''(global_label "{net}" (shape bidirectional) (at {x} {y} {angle})
        (effects (font (size .95 .95)) (justify {'right' if angle==180 else 'left'})) (uuid "{uid('label'+str((net,pos,angle)))}")
        (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {x} {y} 0) (effects (font (size 1 1)) (hide yes))))''')


def nc(pos):
    return parse(f'(no_connect (at {pos[0]} {pos[1]}) (uuid "{uid("nc"+str(pos))}"))')


def text_node(text,x,y,size=1.3):
    return parse(f'(text {json.dumps(text)} (at {x} {y} 0) (effects (font (size {size} {size})) (justify left top)) (uuid "{uid("text"+str((text,x,y)))}"))')


def new_sheet(name,title,paper='A3'):
    sid=uid('sheet'+name);sheet_ids[name]=sid
    return parse(f'''(kicad_sch (version 20231120) (generator "analog_matrix_lc1") (uuid "{sid}") (paper "{paper}")
       (title_block (title "{title}") (date "2026-10-02") (rev "LC1") (company "Analog Programmable Matrix")
       (comment 1 "Separate 12-bit prototype; see simulation model scope and bring-up requirements.")) (lib_symbols))''')


def place(sheet,name,ref,lib,un,x,y,connect=False):
    p=parts[ref]
    s=parse(f'''(symbol (lib_id "AnalogMatrix:{lib}") (at {x} {y} 0) (unit {un}) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)
      (uuid "{uid(name+ref+str(un))}")
      (property "Reference" "{ref}" (at {x} {y-22.86 if lib=='MCP4728T-E_UN' else y-12.7} 0) (effects (font (size 1.05 1.05)) (justify left)))
      (property "Value" "{p['value']}" (at {x} {y-19.56 if lib=='MCP4728T-E_UN' else y-9.4} 0) (effects (font (size .95 .95)) (justify left)))
      (property "Footprint" "{p['footprint']}" (at {x} {y} 0) (effects (font (size 1 1)) (hide yes)))
      (property "Datasheet" "{prop(libs[lib],'Datasheet')[2]}" (at {x} {y} 0) (effects (font (size 1 1)) (hide yes)))
      (property "Rating" {json.dumps(p['rating'])} (at {x} {y} 0) (effects (font (size 1 1)) (hide yes)))
      (instances (project "{PROJECT}" (path "/{root_id}/{sheet_ids[name]}" (reference "{ref}") (unit {un})))))''')
    if lib in ['R_H','C_H']:
        prop(s,'Reference')[3]=parse(f'(at {x} {y-5.08} 0)')
        prop(s,'Value')[3]=parse(f'(at {x} {y-2.54} 0)')
    if ((lib=='OPA4197IPWR' and un==5) or (lib=='OPA2810IDR' and un==3)) or lib=='ADR4525BRZ':
        prop(s,'Reference')[3]=parse(f'(at {x} {y-17.78} 0)')
        prop(s,'Value')[3]=parse(f'(at {x} {y-15.24} 0)')
    if lib=='MCP4728T-E_UN':
        prop(s,'Reference')[3]=parse(f'(at {x+20.32} {y-27.94} 0)')
        prop(s,'Value')[3]=parse(f'(at {x+20.32} {y-24.13} 0)')
    for pin in items(unit(lib,un),'pin'):
        n=pin_number(pin)
        s.append(parse(f'(pin "{n}" (uuid "{uid(name+ref+str(un)+n)}"))'))
    sheet.append(s)
    ps=ports(s)
    if connect:
        intrinsically_nc={pin_number(pin) for pin in items(unit(lib,un),'pin') if pin[1]=='no_connect'}
        for n,pos in ps.items():
            if n in intrinsically_nc:continue
            net=p['pins'][n]
            sheet.append(nc(pos) if net is None else label(net,pos,180 if pos[0]<x else 0))
    return s,ps


def wire(sheet,a,b):
    sheet.append(parse(f'(wire (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})) (stroke (width 0) (type default)) (uuid "{uid("wire"+str((sheet_ids,a,b)))}"))'))


def transform(name):
    sch=parse((BASE/(name+'.kicad_sch')).read_text())
    sheet_ids[name]=base_sheet_ids[name]
    erase_positions=set(); replacements={}; kept=[]
    for s in items(sch,'symbol'):
        ref=str(prop(s,'Reference')[2]);un=int(get(s,'unit')[1]);oldlib=get(s,'lib_id')[1].split(':')[1]
        ps=ports(s)
        if ref.startswith('#'):
            project=get(get(s,'instances'),'project');project[1]=Q(PROJECT)
            path=get(project,'path');path[1]=Q(str(path[1]).replace(old_root,root_id))
            kept.append(s)
            continue
        plan=plans.get(ref)
        target=None
        if plan:
            if 'dacunits' in plan:target=plan['dacunits'].get(un)
            elif un==1:
                u,pm=plan['analog'];target=dict(ref=plan['ref'],lib=plan['lib'],unit=u,pinmap=pm)
            elif plan['power']:
                u,pm=plan['power'];target=dict(ref=plan['ref'],lib=plan['lib'],unit=u,pinmap=pm)
        elif ref in parts:
            target=dict(ref=ref,lib=oldlib,unit=un,pinmap={n:n for n in ps})
        if target is None:
            erase_positions.update(ps.values())
            continue
        pm=target['pinmap'];p=parts[target['ref']]
        for n,pos in ps.items():
            if n not in pm:
                erase_positions.add(pos)
            else:
                oldnet=original[ref]['pins'][n];newnet=p['pins'][pm[n]]
                if oldnet!=newnet:replacements[pos]=newnet
        get(s,'lib_id')[1]=Q('AnalogMatrix:'+target['lib'])
        get(s,'unit')[1]=str(target['unit'])
        prop(s,'Reference')[2]=Q(target['ref'])
        prop(s,'Value')[2]=Q(p['value'])
        prop(s,'Footprint')[2]=Q(p['footprint'])
        prop(s,'Datasheet')[2]=Q(prop(libs[target['lib']],'Datasheet')[2])
        if any(x[1]=='Rating' for x in items(s,'property')):prop(s,'Rating')[2]=Q(p['rating'])
        s[:]=[x for x in s if not (isinstance(x,list) and x[0]=='pin')]
        for pin in items(unit(target['lib'],target['unit']),'pin'):
            n=pin_number(pin);s.append(parse(f'(pin "{n}" (uuid "{uid(name+target["ref"]+n)}"))'))
        inst=get(s,'instances');project=get(inst,'project');project[1]=Q(PROJECT)
        path=get(project,'path');path[1]=Q(str(path[1]).replace(old_root,root_id))
        get(path,'reference')[1]=Q(target['ref']);get(path,'unit')[1]=str(target['unit'])
        kept.append(s)
        for n,pos in ports(s).items():
            if n not in pm.values():
                kept.append(nc(pos) if p['pins'][n] is None else label(p['pins'][n],pos))
    # Follow local wires so removed units leave no orphan supply/control stubs.
    graph={}
    for w in items(sch,'wire'):
        a,b=[(round(float(z[1]),4),round(float(z[2]),4)) for z in get(w,'pts')[1:]]
        graph.setdefault(a,set()).add(b);graph.setdefault(b,set()).add(a)
    def component(start):
        found={start};todo=[start]
        while todo:
            for nxt in graph.get(todo.pop(),set())-found:
                found.add(nxt);todo.append(nxt)
        return found
    kept_ports={pos for s in kept if s[0]=='symbol' for pos in ports(s).values()}
    for pos in list(erase_positions):
        connected=component(pos)
        if not ((connected-erase_positions)&kept_ports):erase_positions.update(connected)
    # A changed net label can be at the far end of a short wire, not at the pin.
    for pos,net in list(replacements.items()):
        for other in component(pos):replacements[other]=net
    out=[]
    for n in sch:
        if not isinstance(n,list):out.append(n);continue
        if n[0] in ('symbol','lib_symbols'):continue
        if n[0] in ('global_label','label','no_connect') and xy(n) in erase_positions:continue
        if n[0] in ('global_label','label','no_connect') and xy(n) in replacements:
            net=replacements[xy(n)]
            if net is None:n=nc(xy(n))
            elif n[0]=='no_connect':n=label(net,xy(n))
            else:n[1]=Q(net)
        if n[0]=='wire':
            pts=get(n,'pts');ends=[(round(float(x[1]),4),round(float(x[2]),4)) for x in pts[1:]]
            if any(p in erase_positions for p in ends):continue
        if n[0]=='text':
            n[1]=Q(str(n[1]).replace('AD5544BRSZ: SSOP-28, 5.3 x 10.2 mm body.','DAC7811: 12-bit; digital/power units on DAC control sheet.').replace('TIA: 2.2pF','TIA: 1.0pF').replace('Rev A2','LC1'))
        out.append(n)
    out.extend(kept)
    title=get(out,'title_block');replace(title,'rev',['rev',Q('LC1')]);replace(title,'date',['date',Q('2026-10-02')])
    if name=='control':
        for n in items(out,'text'):
            if any(w in n[1] for w in ['LDAC','AD5544','RESET','SPI']):
                n[1]=Q('LC1 USB CONTROLLER - 12-bit coefficients and I2C offset trim' if xy(n)[1]<50 else 'SPI mode 1; 1 MHz. Column 3 first, column 0 last.\nGP0/GP1: I2C trim. GP14: output run; outputs default muted.\nAllow 2 ms after trim changes before unmuting.')
            if 'SIGNAL_EN' in n[1]:n[1]=Q('Pico is USB-powered. Do not connect VBUS/VSYS to +5A. Apply analog power first. GP14=OUTPUT_RUN defaults low.')
    return out


def set_library(sch):
    names=sorted({get(s,'lib_id')[1].split(':')[1] for s in items(sch,'symbol')})
    local=['lib_symbols']
    for name in names:
        lib=deepcopy(libs[name]);lib[1]=Q('AnalogMatrix:'+name);local.append(lib)
    replace(sch,'lib_symbols',local)


def trim_sheet():
    name='offset_trim';s=new_sheet(name,'LC1: DC offset correction and precision bias')
    s.append(text_node('DC OFFSET TRIM - I2C, 12-bit, filtered',20.32,20.32,1.8))
    s.append(text_node('Internal reference 2.048 V; gain 1. Code 2500 gives nominal -1.250 V trim.\n10k/10n feedback filters DAC updates. Keep outputs muted for 2 ms after changes.',20.32,30.48))
    _,m=place(s,name,'U400','MCP4728T-E_UN',1,60.96,99.06,True)
    # Label-connected DAC outputs feed four wired inverter/filter stages.
    for i,pm in enumerate(quadmaps):
        y=60.96+i*48.26
        _,a=place(s,name,'U401','OPA4197IPWR',i+1,220.98,y)
        _,ri=place(s,name,f'R{300+2*i}','R_H',1,182.88,y+2.54)
        _,rf=place(s,name,f'R{301+2*i}','R_H',1,220.98,y-17.78)
        _,cf=place(s,name,f'C{320+i}','C_H',1,220.98,y-27.94)
        inv=a[pm['2']];out=a[pm['6']]
        wire(s,ri['2'],(inv[0]-5.08,ri['2'][1]));wire(s,(inv[0]-5.08,ri['2'][1]),(inv[0]-5.08,inv[1]));wire(s,(inv[0]-5.08,inv[1]),inv);s.append(label(f'TRIM_RAW{i}',ri['1'],180));s.append(label('GND',a[pm['3']],180))
        # Symbol R_H pin 1 is left: orient nets in the part map to match wiring.
        parts[f'R{301+2*i}']['pins']={'1':f'TN{i}','2':f'VTRIM{i}'}
        parts[f'C{320+i}']['pins']={'1':f'TN{i}','2':f'VTRIM{i}'}
        for pp in [rf,cf]:
            wire(s,pp['1'],(inv[0],pp['1'][1]));wire(s,(inv[0],pp['1'][1]),inv)
            wire(s,pp['2'],(out[0],pp['2'][1]));wire(s,(out[0],pp['2'][1]),out)
        s.append(label(f'VTRIM{i}',out))
        s.append(text_node(f'Row {i}',147.32,y-12.7))
    place(s,name,'U401','OPA4197IPWR',5,60.96,205.74,True)
    for ref,x,y in [('C324',101.6,152.4),('C327',132.08,152.4),('C325',30.48,243.84),('C326',81.28,243.84),('R308',25.4,152.4),('R309',63.5,152.4)]:
        place(s,name,ref,'R_V' if ref.startswith('R') else 'C_V',1,x,y,True)
    # Reuse the original reference drawing as a labeled standalone block.
    original_sheet=parse((BASE/'offset_trim.kicad_sch').read_text())
    for old_s in items(original_sheet,'symbol'):
        ref=prop(old_s,'Reference')[2]
        if ref not in ['U110','C187','C188','C189','C190']:continue
        lib=get(old_s,'lib_id')[1].split(':')[1];un=int(get(old_s,'unit')[1])
        loc={'U110':(340.36,73.66),'C187':(302.26,127),'C188':(335.28,127),'C189':(368.3,127),'C190':(368.3,165.1)}[ref]
        place(s,name,ref,lib,un,*loc,connect=True)
    s.append(text_node('2.5 V SUMMING BIAS',299.72,35.56,1.5))
    return s


def dac_sheet():
    name='dac_control';s=new_sheet(name,'LC1: DAC row chains, power and local bypass',paper='A2')
    s.append(text_node('DAC7811 - FOUR INDEPENDENT ROW CHAINS',20.32,20.32,1.8))
    s.append(text_node('5 V DAC supplies; 3.3 V SPI inputs meet VIH. SDO is 5 V: connect only to the next DAC.\nSPI mode 1, 1 MHz. Send column 3 first, column 0 last; each SYNC rising edge updates its row.\nEach 100 nF bypass must sit at its DAC supply pins. Analog units are on their output-row sheets.',20.32,30.48))
    for row in range(4):
        y=83.82+row*76.2
        for j in range(4):
            x=66.04+j*129.54
            s.append(text_node(f'ROW {row} / COLUMN {j}',x-20.32,y-33.02))
            symbol,ps=place(s,name,f'U{300+4*row+j}','DAC7811IDGSR',2,x,y,True)
            # Keep label/value clear of the supply pin.
            prop(symbol,'Reference')[3]=parse(f'(at {x+22.86} {y-20.32} 0)')
            prop(symbol,'Value')[3]=parse(f'(at {x+22.86} {y-16.51} 0)')
            place(s,name,f'C{300+4*row+j}','C_V',1,x+50.8,y+5.08,True)
    return s


def main():
    # KiCad represents unconnected package pads with passive pins plus NC markers.
    for name in ['TMUX6136PWR','DAC7811IDGSR','MCP4728T-E_UN']:
        for u in items(libs[name],'symbol'):
            for pin in items(u,'pin'):
                if pin[1]=='no_connect':pin[1]='passive'
    DEST.mkdir(parents=True,exist_ok=True)
    for name in ['AnalogMatrix.pretty','models']:
        if not (DEST/name).exists():shutil.copytree(BASE/name,DEST/name)
    for name in ['fp-lib-table','sym-lib-table','KiCad-footprints-LICENSE.txt']:
        shutil.copy2(BASE/name,DEST/name)
    for name in ['VSSOP-10_3x3mm_P0.5mm','MSOP-10_3x3mm_P0.5mm','TSSOP-16_4.4x5mm_P0.65mm','TSSOP-14_4.4x5mm_P0.65mm']:
        source=Path('C:/Program Files/KiCad/8.0/share/kicad/footprints/Package_SO.pretty')/(name+'.kicad_mod')
        shutil.copy2(source,DEST/'AnalogMatrix.pretty'/source.name)
    names=['inputs']+[f'row_{i}' for i in range(4)]+['control','power']
    sheets={name:transform(name) for name in names}
    sheets['offset_trim']=trim_sheet();sheets['dac_control']=dac_sheet()
    for name,sch in sheets.items():
        set_library(sch)
        (DEST/(name+'.kicad_sch')).write_text(dumps(sch)+'\n',encoding='utf-8')
    root=parse((BASE/'analog_matrix_4x4.kicad_sch').read_text())
    get(root,'uuid')[1]=Q(root_id)
    get(get(root,'title_block'),'rev')[1]=Q('LC1')
    get(get(root,'title_block'),'date')[1]=Q('2026-10-02')
    get(get(root,'title_block'),'title')[1]=Q('Analog Programmable Matrix - LC1 lower-cost alternative')
    for child in items(root,'sheet'):
        name=prop(child,'Sheetfile')[2].removesuffix('.kicad_sch')
        if name in sheet_ids:get(child,'uuid')[1]=Q(sheet_ids[name])
    extra=deepcopy(items(root,'sheet')[-1])
    get(extra,'uuid')[1]=Q(sheet_ids['dac_control']);get(extra,'at')[1:]=['279.4','152.4']
    prop(extra,'Sheetname')[2]=Q('DAC digital and supplies');prop(extra,'Sheetfile')[2]=Q('dac_control.kicad_sch')
    # Property positions translate with the added root sheet.
    for p in items(extra,'property'):
        a=get(p,'at')
        if a:a[1]='279.4';a[2]='147.32' if p[1]=='Sheetname' else '177.8'
    root.append(extra)
    for n in items(root,'text'):
        if any(v in n[1] for v in ['AD5544','16-bit','A2','Revision','16 bit']):
            n[1]=Q('LC1: 12-bit multiplying DACs; consolidated dual/quad packages.\nOriginal Revision D is preserved in pcb/analog_matrix_4x4_rev_d.\nPrototype: circuit simulation is not hardware qualification.')
    def fix_project(n):
        if not isinstance(n,list):return
        if n and n[0]=='project':n[1]=Q(PROJECT)
        if n and n[0]=='path' and len(n)>1 and isinstance(n[1],str):n[1]=Q(n[1].replace(old_root,root_id))
        for x in n:fix_project(x)
    fix_project(root)
    (DEST/(PROJECT+'.kicad_sch')).write_text(dumps(root)+'\n',encoding='utf-8')
    proj=json.loads((BASE/'analog_matrix_4x4.kicad_pro').read_text())
    (DEST/(PROJECT+'.kicad_pro')).write_text(json.dumps(proj,indent=2))
    (DEST/'AnalogMatrix.kicad_sym').write_text(dumps(['kicad_symbol_lib',['version','20231120'],['generator',Q('analog_matrix_lc1')],*libs.values()])+'\n')
    # Root instances provide board-to-schematic association for every package.
    instances={}
    for name,sch in sheets.items():
        for s in items(sch,'symbol'):
            ref=prop(s,'Reference')[2]
            if ref not in parts:continue
            instances.setdefault(ref,dict(path=f'/{root_id}/{sheet_ids[name]}/{get(s,"uuid")[1]}',sheet=name))
    manifest=dict(parts=list(parts.values()),instances=instances,plans=plans,
                  baseline_board_sha256=hashlib.sha256((BASE/'analog_matrix_4x4.kicad_pcb').read_bytes()).hexdigest(),
                  revision='LC1',date='2026-10-02')
    (DEST/'design_instances.json').write_text(json.dumps(manifest,indent=2))
    print('LC1 parts',len(parts),'SMT candidates',sum(p['ref'][0] in 'RCU' and p['ref'] not in ['U120','U130','U131'] for p in parts.values()))
    print('Missing schematic instances',sorted(set(parts)-set(instances)))


if __name__=='__main__':main()
