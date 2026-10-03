"""Generate and run LC1 circuit-level benches without changing Revision D evidence."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(REPO / 'spice'))
from read_raw import read_raw

HEADER = '''* LC1: datasheet-derived static MDAC and switch model; vendor op amps.
.include "../vendor/opa2810/opa2810_a.lib"
.include "../../../../spice/models/ADA4899.sub"
.include "../../../../spice/models/ths3091_tina/THS3091.lib"
.include "../../../../spice/models/opa197/OPAx197.LIB"
.param rdac=10k ron=120 csw=7.5p cout=5p cstray=5p cf=1p cfstray=.3p fbw=10Meg q=.93552 sg=0 cload=20p
VP vp 0 5
VN vn 0 -5
VHP hp 0 15
VHN hn 0 -15
VREF vref 0 2.5
.options plotwinsize=0 numdgt=7 reltol=.001 abstol=1p vntol=1u method=gear
'''


def frontend(i, source):
    lines = [f'VIN{i} a{i} 0 {source}', f'Rin{i} a{i} ai{i} 33', f'Rb{i} a{i} 0 1Meg',
             f'Xbuf{i} ai{i} buf{i} buf{i} vp vn OPA2810',
             f'Rp1_{i} buf{i} pd{i} 499', f'Rp2_{i} pd{i} 0 499',
             f'Xpos{i} pd{i} pi{i} p{i} vp vn OPA2810',
             f'Rpf{i} p{i} pi{i} 1k', f'Rpg{i} pi{i} 0 1k',
             f'Xneg{i} 0 ni{i} n{i} vp vn OPA2810',
             f'Rni{i} buf{i} ni{i} 1k', f'Rnf{i} n{i} ni{i} 1k']
    for row in range(4):
        suf = f'{i}_{row}'
        lines += [f'Rbp{suf} p{i} sp{suf} 150', f'Rbn{suf} n{i} sn{suf} 150',
                  f'Cp{suf} sp{suf} 0 {{csw}}', f'Cn{suf} sn{suf} 0 {{csw}}',
                  f'Rswp{suf} sp{suf} ref{suf} {{if(sg<.5,ron,1T)}}',
                  f'Rswn{suf} sn{suf} ref{suf} {{if(sg>.5,ron,1T)}}',
                  f'Rref{suf} ref{suf} 0 {{rdac}}', f'Cref{suf} ref{suf} 0 5p']
    # Independent 10 MHz pole is a conservative bandwidth allowance, not an
    # exact manufacturer model. It is swept as an explicit uncertainty.
    lines += [f'Ebw{i} bwsource{i} 0 ref{i}_0 0 1',
              f'Rbw{i} bwsource{i} filt{i} 1k', f'Cbw{i} filt{i} 0 {{1/(2*pi*1k*fbw)}}',
              f'Gdac{i} 0 inn{i} filt{i} 0 {{q/rdac}}',
              f'Rfb{i} weight{i} inn{i} {{rdac}}',
              f'Rout{i} inn{i} 0 {{rdac}}', f'Co{i} inn{i} 0 {{cout+cstray}}',
              f'Cf{i} weight{i} inn{i} {{cf+cfstray}}',
              f'Xamp{i} 0 inn{i} vp vn weight{i} weight{i} vp ADA4899',
              f'Rsum{i} weight{i} snode 1k']
    return '\n'.join(lines) + '\n'


TAIL = '''Rt snode trim 10k
Vtrim trim 0 -1.25
Rrefsum snode vref 20k
Rsf sum snode 549
Xsum 0 snode sum vp vn OPA2810
Rmute sum mute_source 49.9
Rmuteon mute_source drv {ron}
Cmuteload drv 0 {csw+10p}
Rbias drv 0 100k
Xdrv drv dn dout hp hn THS3091
Rdf dout dn 1210
Rdg dn 0 402
Rser dout b0 49.9
Rl b0 0 50
Cl b0 0 {cload}
.save V(a0) V(ref0_0) V(weight0) V(sum) V(dout) V(b0)
'''


def bench(name, kind='ac', params='', sources=None):
    sources = sources or ['AC 1'] + ['0'] * 3
    text = HEADER + ''.join(frontend(i, s) for i, s in enumerate(sources)) + TAIL
    if params:
        for key,value in re.findall(r'(\w+)=([^\s]+)',params):
            text=re.sub(r'(?<!\w)'+key+r'=[^\s]+',key+'='+value,text,count=1)
    text += {'ac': '.ac dec 160 100 100Meg', 'dc': '.dc VIN0 0 1 .01',
             'tran': '.tran 0 12u 0 2n'}[kind] + '\n.end\n'
    return name, text


def loop_benches():
    finish = "VTEST out raw DC 0 AC 1\n.ac dec 150 10 3G\n.save V(out) V(raw)\n.end\n"
    jobs=[]
    for resistance in [8000,10000,12000]:
        for capacitance in [10,20]:
            for feedback in [1.1,1.5]:
                circuit=(f"XAMP 0 inn vp vn raw raw vp ADA4899\n"
                         f"RF out inn {resistance}\nRO inn 0 {resistance}\nCO inn 0 {capacitance}p\n"
                         f"CF out inn {feedback}p\nRL out 0 1k\nCL out 0 20p\n")
                jobs.append((f"loop_tia_r{resistance}_c{capacitance}_f{feedback}",HEADER+circuit+finish))
    summer="XAMP 0 inn raw vp vn OPA2810\nRF out inn 549\nRIN inn 0 {1/(4/1000+1/10000+1/20000)}\nCI inn 0 10p\nRS out load 169.9\nCL load 0 30p\nRL load 0 100k\n"
    jobs.append(('loop_summer',HEADER+summer+finish))
    for cl in [20,1000]:
        circuit=f"XAMP 0 inn raw hp hn THS3091\nRF out inn 1210\nRG inn 0 402\nRS out load 49.9\nRL load 0 50\nCL load 0 {cl}p\n"
        jobs.append((f'loop_driver_{cl}p',HEADER+circuit+finish))
    for name,old,new,fb in [('buffer','Xbuf0 ai0 buf0 buf0','Xbuf0 ai0 sense buf0','buf0'),
                            ('positive','Xpos0 pd0 pi0 p0','Xpos0 pd0 sense p0','pi0'),
                            ('negative','Xneg0 0 ni0 n0','Xneg0 0 sense n0','ni0')]:
        for sign in [0,1]:
            circuit=frontend(0,'0').split('Ebw0')[0].replace(old,new)
            header=HEADER.replace('sg=0',f'sg={sign}')
            jobs.append((f'loop_input_{name}_sign{sign}',header+circuit+f'VTEST sense {fb} DC 0 AC 1\nEOUT out 0 sense 0 1\nERAW raw 0 {fb} 0 1\n.ac dec 150 10 3G\n.save V(out) V(raw)\n.end\n'))
    trim="XAMP 0 inn vp vn raw OPAx197\nRF out inn 10k\nCF out inn 10n\nRIN inn 0 10k\nRL out 0 10k\nCL out 0 30p\n"
    jobs.append(('loop_trim',HEADER+trim+finish))
    return jobs


def generate():
    jobs = [bench('row_ac'), bench('row_ac_negative', params='.param sg=1'),
            bench('row_ac_half', params='.param q=.5'),
            bench('row_ac_tenth', params='.param q=.1'),
            bench('row_ac_bandwidth_stress', params='.param fbw=5Meg'),
            bench('row_ac_low_r', params='.param rdac=8k cout=10p cstray=10p cfstray=.5p ron=245'),
            bench('row_ac_high_r', params='.param rdac=12k cout=10p cstray=10p cfstray=.5p ron=245'),
            bench('row_dc', kind='dc', sources=['0'] * 4),
            bench('row_dc_negative', kind='dc', sources=['0'] * 4, params='.param sg=1'),
            tuple((lambda n,t:(n,t.replace('.dc VIN0 0 1 .01','.dc VIN0 0 -1 -.01')))(*bench('row_dc_input_negative',kind='dc',sources=['0']*4))),
            bench('row_sine', kind='tran', sources=['SINE(0 1 1Meg)'] * 4),
            bench('row_step', kind='tran', sources=['PULSE(0 1 1u 10n 10n 5u 12u)'] * 4),
            bench('row_step_1nf', kind='tran', sources=['PULSE(0 1 1u 10n 10n 5u 12u)'] * 4, params='.param cload=1n')]
    jobs += loop_benches()
    folder = ROOT / 'simulation' / 'benches'
    folder.mkdir(parents=True, exist_ok=True)
    for name, text in jobs:
        (folder / (name + '.cir')).write_text(text)
    return folder


def run(path, timeout=180):
    exe = Path(os.environ['LOCALAPPDATA']) / 'Programs/ADI/LTspice/LTspice.exe'
    start = time.monotonic()
    info = {'bench': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    try:
        proc = subprocess.run([str(exe), '-b', str(path)], cwd=path.parent,
                              creationflags=subprocess.CREATE_NO_WINDOW, timeout=timeout,
                              capture_output=True)
        info['returncode'] = proc.returncode
        log = path.with_suffix('.log').read_text(errors='replace')
        if 'Fatal Error' in log or not path.with_suffix('.raw').exists():
            raise RuntimeError(log[-2000:])
        meta, v = read_raw(path.with_suffix('.raw'))
        info['points'] = len(next(iter(v.values())))
        if 'frequency' in v:
            freq = v['frequency'].real
            if 'v(b0)' not in v:
                loop=-v['v(raw)']/v['v(out)']
                db=20*np.log10(np.abs(loop))
                phase=np.unwrap(np.angle(loop))*180/np.pi
                crossings=np.where((db[:-1]>=0)&(db[1:]<0))[0]
                margins=[]
                for i in crossings:
                    f=-db[i]/(db[i+1]-db[i])
                    margins.append(dict(crossover_hz=float(np.exp(np.log(freq[i])+f*np.log(freq[i+1]/freq[i]))),
                                        phase_margin_deg=float(180+phase[i]+f*(phase[i+1]-phase[i]))))
                if not margins:raise RuntimeError('No unity-loop crossover found')
                info.update(loop_crossings=margins,min_phase_margin_deg=min(x['phase_margin_deg'] for x in margins))
                info['status']='completed';info['seconds']=time.monotonic()-start
                path.with_suffix('.result.json').write_text(json.dumps(info,indent=2))
                print(json.dumps(info),flush=True)
                return info
            gain = v['v(b0)']
            norm = np.abs(gain / gain[0])
            k = int(np.argmin(abs(freq - 1e6)))
            info.update(dc_gain=float(abs(gain[0])), gain_at_1mhz=float(abs(gain[k])),
                        normalized_gain_at_1mhz=float(norm[k]),
                        magnitude_error_1mhz_percent=float(100 * (norm[k] - 1)),
                        passband_peak_percent=float(100 * (max(norm[freq <= 1e6]) - 1)))
        elif 'time' in v:
            t = v['time']
            out = v['v(b0)']
            info.update(end_time=float(t[-1]), minimum=float(min(out)), maximum=float(max(out)))
            if t[-1] < 11.99e-6:
                raise RuntimeError('Transient did not reach its requested stop time')
            if 'step' in path.stem:
                steady = float(np.median(out[(t > 4e-6) & (t < 5e-6)]))
                info['steady_voltage'] = steady
                info['overshoot_percent'] = float(100 * (max(out) / steady - 1))
        else:
            x = next(iter(v.values()))
            fit = np.polyfit(x, v['v(b0)'], 1)
            info.update(dc_slope=float(fit[0]), dc_offset=float(fit[1]),
                        max_residual_v=float(max(abs(v['v(b0)'] - np.polyval(fit, x)))))
        info['status'] = 'completed'
    except Exception as exc:
        info.update(status='unresolved', error=str(exc))
    info['seconds'] = time.monotonic() - start
    path.with_suffix('.result.json').write_text(json.dumps(info, indent=2))
    print(json.dumps(info), flush=True)
    return info


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bench')
    parser.add_argument('--loops-only',action='store_true')
    parser.add_argument('--generate-only', action='store_true')
    args = parser.parse_args()
    folder = generate()
    if not args.generate_only:
        paths = [folder / (args.bench + '.cir')] if args.bench else sorted(folder.glob('loop*.cir' if args.loops_only else '*.cir'))
        results = [run(p) for p in paths]
        # Aggregate current recorded benches; a focused rerun must not erase others.
        recorded=[json.loads(p.read_text()) for p in folder.glob('*.result.json')]
        for record in recorded:
            circuit=folder/record['bench']
            record['evidence_matches_netlist']=hashlib.sha256(circuit.read_bytes()).hexdigest()==record['sha256']
        (ROOT/'simulation/results.json').write_text(json.dumps(recorded,indent=2))
        (ROOT/'simulation/loops.json').write_text(json.dumps([r for r in recorded if r['bench'].startswith('loop')],indent=2))
