"""Package the current CAD and check files; electrical exports are separate."""
from pathlib import Path
import hashlib,json,zipfile
R=Path(__file__).resolve().parents[1]
M=R/'mechanical/analog_matrix_package_m3';O=R/'output';O.mkdir(exist_ok=True)
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest={str(p.relative_to(M)).replace('\\','/'):digest(p) for p in M.rglob('*')
 if p.is_file() and p.name!='SHA256.json' and '__pycache__' not in p.parts and p.suffix not in ['.lck','.kicad_prl','.blend1']}
(M/'SHA256.json').write_text(json.dumps(manifest,indent=2))
target=O/'analog_matrix_3d_and_enclosure_M3.zip'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
 for name in list(manifest)+['SHA256.json']:z.write(M/name,str(Path(M.name)/name))
archives=['analog_matrix_4x4_rev_d_pcb.zip','analog_matrix_4x4_rev_d_fabrication.zip',
 'analog_matrix_rev_d_JLCPCB_handoff.zip','analog_matrix_3d_and_enclosure_M3.zip']
for name in archives:
 with zipfile.ZipFile(O/name) as z:assert z.testzip() is None,name
(O/'release_manifest.json').write_text(json.dumps({'release':'v0.1.0','pcb':'D','enclosure':'M3',
 'added_power_led':False,'archives':{name:digest(O/name) for name in archives}},indent=2))
print('Release archives and checksums verified.')
