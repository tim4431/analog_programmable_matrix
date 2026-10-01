"""Create a separate 3D-enabled board without modifying the verified PCB."""
from pathlib import Path
import pcbnew as k, json, shutil, hashlib
ROOT=Path(__file__).resolve().parents[1]
S=ROOT/'pcb/analog_matrix_4x4_rev_d';D=ROOT/'mechanical/analog_matrix_package_m3'
manifest={r['reference']:r['model'] for r in json.loads((D/'model_manifest.json').read_text())}
original=S/'analog_matrix_4x4.kicad_pcb'
before=hashlib.sha256(original.read_bytes()).hexdigest()
b=k.LoadBoard(str(original))
for f in b.GetFootprints():
    ref=f.GetReference()
    if ref.startswith('H'):continue
    name=manifest.get(ref,'R_0603_1608Metric.step')
    f.Models().clear()
    m=k.FP_3DMODEL();m.m_Filename='${KIPRJMOD}/models/'+name
    f.Models().push_back(m)
out=D/'analog_matrix_4x4_3d.kicad_pcb';k.SaveBoard(str(out),b)
shutil.copy2(S/'analog_matrix_4x4.kicad_pro',D/'analog_matrix_4x4_3d.kicad_pro')
shutil.copytree(S/'AnalogMatrix.pretty',D/'AnalogMatrix.pretty',dirs_exist_ok=True)
shutil.copy2(S/'fp-lib-table',D/'fp-lib-table')
# Update the copied local footprint models too, so library comparison is useful.
for fp in (D/'AnalogMatrix.pretty').glob('*.kicad_mod'):
    f=k.FootprintLoad(str(D/'AnalogMatrix.pretty'),fp.stem)
    match=next((v for r,v in manifest.items() if str(next(g for g in b.GetFootprints() if g.GetReference()==r).GetFPID().GetLibItemName())==fp.stem),None)
    if match:
        f.Models().clear();m=k.FP_3DMODEL();m.m_Filename='${KIPRJMOD}/models/'+match;f.Models().push_back(m)
        k.FootprintSave(str(D/'AnalogMatrix.pretty'),f)
assert hashlib.sha256(original.read_bytes()).hexdigest()==before
print('3D board saved; original verified PCB unchanged.')
