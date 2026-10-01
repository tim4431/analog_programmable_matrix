"""Replay an included bench with LTspice for Windows, without opening a window."""
from pathlib import Path
import argparse,subprocess,os,json,time,hashlib

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ltspice',type=Path,default=Path(os.environ.get('LOCALAPPDATA',''))/'Programs/ADI/LTspice/LTspice.exe')
    parser.add_argument('--bench',default='a2_row_sine_rc.cir',help='Filename inside benches/')
    parser.add_argument('--timeout',type=int,default=300)
    args=parser.parse_args();root=Path(__file__).resolve().parent
    file=(root/'benches'/args.bench).resolve()
    if file.parent!=(root/'benches').resolve() or not file.is_file():parser.error('Choose an existing file inside benches/.')
    if not args.ltspice.is_file():parser.error('Use --ltspice with the installed LTspice.exe path.')
    # Preserve delivered proof: run a copy in a sibling directory with the same
    # ../models relative includes, rather than overwriting reference waveforms.
    dest=root/'reruns';dest.mkdir(exist_ok=True);target=dest/file.name
    target.write_bytes(file.read_bytes())
    si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    start=time.monotonic()
    try:
        p=subprocess.run([str(args.ltspice),'-b',str(target)],cwd=dest,startupinfo=si,creationflags=subprocess.CREATE_NO_WINDOW,timeout=args.timeout,capture_output=True)
        result={'exitcode':p.returncode,'seconds':time.monotonic()-start}
    except subprocess.TimeoutExpired:
        result={'status':'UNRESOLVED','reason':'Timeout','seconds':time.monotonic()-start}
    result['netlist_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix('.result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2));print('Outputs:',dest)
    print('Check simulator log and trace completeness before interpreting results.')
if __name__=='__main__':main()
