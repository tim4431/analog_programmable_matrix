"""Fetch vendor models locally. Vendor files are not redistributed in Git."""
from pathlib import Path
import hashlib
import io
import json
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
JOBS = {
    'opa2810': 'https://www.ti.com/lit/zip/SBOMB66',
    'dac7811': 'https://www.ti.com/lit/zip/SBAM488',
}


def main():
    records = []
    for name, url in JOBS.items():
        folder = ROOT / 'simulation' / 'vendor' / name
        folder.mkdir(parents=True, exist_ok=True)
        archive = folder.parent / (name + '.zip')
        if not archive.exists():
            request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(request, timeout=90) as response:
                archive.write_bytes(response.read())
        data = archive.read_bytes()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for member in z.infolist():
                assert (folder / member.filename).resolve().is_relative_to(folder.resolve())
            z.extractall(folder)
            files = z.namelist()
        records.append(dict(name=name, url=url, sha256=hashlib.sha256(data).hexdigest(), files=files))
        print(name, files)
    (ROOT / 'simulation' / 'vendor_provenance.json').write_text(json.dumps(records, indent=2))


if __name__ == '__main__':
    main()
