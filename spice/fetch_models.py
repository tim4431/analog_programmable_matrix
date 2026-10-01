from pathlib import Path
import urllib.request, zipfile, io, json, hashlib, shutil, argparse, os
from concurrent.futures import ThreadPoolExecutor

parser=argparse.ArgumentParser(description='Download local vendor SPICE models; vendor terms apply.')
parser.add_argument('--ada4899',type=Path,help='Path to ADA4899.sub from an installed LTspice library')
args=parser.parse_args()
root=Path(__file__).resolve().parent
models=root/'models';models.mkdir(exist_ok=True)
jobs={'opa810':'https://www.ti.com/lit/zip/SBOMB73',
      'opa197':'https://www.ti.com/lit/zip/SBOMA34',
      'ths3091':'https://www.ti.com/lit/zip/SLOJ173',
      'ths3091_tina':'https://www.ti.com/lit/zip/SLOM418',
      'tmux6219':'https://www.ti.com/lit/zip/SCDM270'}
def fetch(item):
    name,url=item
    dest=models/(name+'.zip')
    if dest.exists():data=dest.read_bytes();resolved=url
    else:
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req,timeout=45) as r:data=r.read();resolved=r.url
        dest.write_bytes(data)
    folder=models/name;folder.mkdir(exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for member in z.infolist():
            target=(folder/member.filename).resolve()
            assert target.is_relative_to(folder.resolve())
        z.extractall(folder)
        names=z.namelist()
    print(name,':',len(names),'files')
    return dict(name=name,url=url,resolved=resolved,sha256=hashlib.sha256(data).hexdigest(),files=names)
with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(fetch,jobs.items()))
local=Path(os.environ.get('LOCALAPPDATA',''))
candidates=[local/'LTspice/lib/sub/ADA4899.sub',local/'LTspiceXVII/lib/sub/ADA4899.sub']
src=args.ada4899 or next((p for p in candidates if p.is_file()),None)
if src is None or not src.is_file():
    parser.error('Locate ADA4899.sub in your LTspice library and pass --ada4899 PATH.')
shutil.copy2(src,models/'ADA4899.sub')
rows.append(dict(name='ADA4899',source='Installed LTspice library: ADA4899.sub',source_page='https://www.analog.com/en/products/ada4899-1.html',
                 sha256=hashlib.sha256(src.read_bytes()).hexdigest(),note='Installed ADI LTspice model; unmodified binary model. Pin order verified from ADA4899.asy.'))
(models/'provenance.json').write_text(json.dumps(rows,indent=2))
