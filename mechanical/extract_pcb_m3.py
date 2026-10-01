"""Read-only extraction of the verified PCB and package its 3D assets."""
from pathlib import Path
import pcbnew as k
import json, shutil, hashlib

ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'pcb/analog_matrix_4x4_rev_d'
OUT=ROOT/'mechanical/analog_matrix_package_m3'
OUT.mkdir(parents=True,exist_ok=True)
MODELS=OUT/'models'; MODELS.mkdir(exist_ok=True)
LIB=Path(r'C:\Program Files\KiCad\8.0\share\kicad\3dmodels')
b=k.LoadBoard(str(D/'analog_matrix_4x4.kicad_pcb'))
parts=[]
for f in b.GetFootprints():
    ref=f.GetReference(); fp=str(f.GetFPID().GetLibItemName())
    p={'ref':ref,'value':f.GetValue(),'footprint':fp,
       'x':k.ToMM(f.GetPosition().x),'y':k.ToMM(f.GetPosition().y),
       'rotation':f.GetOrientationDegrees(),'dnp':f.IsDNP(),
       'smd':bool(f.GetAttributes() & k.FP_SMD), 'models':[], 'pads':[]}
    for m in f.Models():
        source=Path(m.m_Filename.replace('${KICAD8_3DMODEL_DIR}',str(LIB))).with_suffix('.step')
        exists=source.exists()
        if exists: shutil.copy2(source,MODELS/source.name)
        p['models'].append({'file':source.name,'available':exists,
          'offset':[m.m_Offset.x,m.m_Offset.y,m.m_Offset.z],
          'scale':[m.m_Scale.x,m.m_Scale.y,m.m_Scale.z],
          'rotation':[m.m_Rotation.x,m.m_Rotation.y,m.m_Rotation.z]})
    for pad in f.Pads():
        p['pads'].append({'number':pad.GetNumber(),'x':k.ToMM(pad.GetPosition().x),'y':k.ToMM(pad.GetPosition().y),
            'sx':k.ToMM(pad.GetSize().x),'sy':k.ToMM(pad.GetSize().y),
            'drill':[k.ToMM(pad.GetDrillSize().x),k.ToMM(pad.GetDrillSize().y)],
            'rotation':pad.GetOrientationDegrees(),'shape':int(pad.GetShape())})
    parts.append(p)
out={'source_sha256':hashlib.sha256((D/'analog_matrix_4x4.kicad_pcb').read_bytes()).hexdigest(),
     'width':160,'depth':170,'thickness':1.6,'parts':parts}
(OUT/'pcb_geometry.json').write_text(json.dumps(out,indent=2))
unique={p['footprint']:p['models'] for p in parts if not p['ref'].startswith('H')}
print(json.dumps(unique,indent=2))

