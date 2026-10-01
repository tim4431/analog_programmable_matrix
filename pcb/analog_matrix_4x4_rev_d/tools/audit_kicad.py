"""Compare KiCad's exported connectivity to the intended pin-level design."""
from pathlib import Path
from collections import Counter,defaultdict
import json,xml.etree.ElementTree as ET,re,sys
root=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).parent/'analog_matrix_4x4'
data=json.loads((root/'design_instances.json').read_text(encoding='utf-8'))
pins={};expected=defaultdict(set);parts={}
for p in data['parts']:
    parts[p['ref']]=p
    for pin,net in p['pins'].items():
        pair=(p['ref'],pin);pins[pair]=net
        if net is not None:expected[net].add(pair)
xml=ET.parse(root/'validation_netlist.xml').getroot()
actual={};actual_sets={};unknown=[]
for net in xml.findall('./nets/net'):
    name=net.get('name');ns=set()
    for node in net.findall('node'):
        pair=(node.get('ref'),node.get('pin'))
        if pair[0].startswith('#'):continue
        ns.add(pair);actual[pair]=name
        if pair not in pins:unknown.append(pair)
    actual_sets[name]=ns
errors=[]
for name,ns in expected.items():
    names={actual.get(p) for p in ns}
    if len(names)!=1 or None in names:
        groups={str(n):sorted(p for p in ns if actual.get(p)==n) for n in names}
        errors.append({'expected_net':name,'split_or_missing':groups})
    for n in names:
        extra=actual_sets.get(n,set())-ns
        if extra:errors.append({'expected_net':name,'actual_net':n,'unintended_members':sorted(extra)})
for pair,net in pins.items():
    if net is None and pair in actual and len(actual_sets[actual[pair]])>1:errors.append({'NC_connected':pair,'net':actual[pair]})
if unknown:errors.append({'unknown_pins':unknown})
components={c.get('ref') for c in xml.findall('./components/comp')}
if components!=set(parts):errors.append({'component_mismatch':sorted(components^set(parts))})
erc=json.loads((root/'erc.json').read_text(encoding='utf-8'))
counts=Counter(v['type'] for s in erc['sheets'] for v in s['violations'])
print('ERC types:',dict(counts))
shown=Counter()
for s in erc['sheets']:
    for v in s['violations']:
        if shown[v['type']]<2:
            print(v['type'],s['path'],v['description'],[x['description'] for x in v['items']]);shown[v['type']]+=1
print('Connectivity errors:',len(errors))
for e in errors[:30]:
    if 'split_or_missing' in e:
        print('SPLIT',e['expected_net'],{k:v[:6] for k,v in e['split_or_missing'].items()})
    elif 'unintended_members' in e:
        print('EXTRA',e['expected_net'],e['actual_net'],e['unintended_members'][:6])
    else:print(e)
print('Unconnected pins:')
for s in erc['sheets']:
    for v in s['violations']:
        if v['type']=='pin_not_connected':print(v['items'][0]['description'],v['items'][0]['pos'])
(root/'connectivity_audit.json').write_text(json.dumps({'components':len(parts),'expected_connected_pins':sum(len(x) for x in expected.values()),'expected_nets':len(expected),'connectivity_errors':errors,'erc_counts':dict(counts)},indent=2))
if errors or counts:raise SystemExit(1)
