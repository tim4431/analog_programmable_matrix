"""Check all exported component pin numbers against their assigned local pads."""
import json,re,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).parent/'analog_matrix_4x4'
data=json.loads((root/'design_instances.json').read_text(encoding='utf-8'))
errors=[];assignments=[]
for p in data['parts']:
    lib,name=p['footprint'].split(':')
    file=root/(lib+'.pretty')/(name+'.kicad_mod')
    assert file.is_file(),file
    padnums=set(re.findall(r'\(pad\s+"([^"]+)"',file.read_text(encoding='utf-8')))
    pins=set(p['pins'])
    if padnums!=pins:errors.append({'reference':p['ref'],'pads_without_pins':sorted(padnums-pins),'pins_without_pads':sorted(pins-padnums)})
    assignments.append({'reference':p['ref'],'original':p['old_ref'],'value':p['value'],'footprint':p['footprint'],'pads':sorted(padnums),'dnp':p['dnp'],'rating':p['rating']})
ada=(root/'AnalogMatrix.pretty/ADA4899_RD8_EP2.29x2.29.kicad_mod').read_text()
assert '(pad "9" smd rect (at 0 0) (size 2.29 2.29)' in ada
pico=(root/'AnalogMatrix.pretty/Pico_2x20_Socket_17.78mm.kicad_mod').read_text()
assert '(pad "1" thru_hole rect (at -8.89 -24.13)' in pico
assert '(pad "40" thru_hole oval (at 8.89 -24.13)' in pico
for p in data['parts']:
    if p['polarized']:
        a,b=p['pins']['1'],p['pins']['2']
        assert not a.startswith('-'),(p['ref'],'reversed positive electrode')
        assert not b.startswith('+'),(p['ref'],'reversed negative electrode')
report={'components':len(assignments),'footprints':len(set(x['footprint'] for x in assignments)),'pad_number_errors':errors,'polarized_capacitor_orientation':'checked: pad 1 positive, pad 2 negative','assignments':assignments}
(root/'footprint_audit.json').write_text(json.dumps(report,indent=2))
print('Footprint audit:',len(assignments),'components;',report['footprints'],'unique footprints;',len(errors),'pin/pad mismatches')
if errors:
    print(errors);raise SystemExit(1)
