"""Drive the max_features sensitivity matrix with bounded concurrency.

PowerShell's Wait-Process is blocked by the sandbox, so the orchestrator is Python and
polls its own children (stdout goes to files, never pipes).
"""
from pathlib import Path
import subprocess
import sys
import time
import datetime
import argparse

P = Path(__file__).resolve().parents[1]
PY = r'C:\Users\汪星人\AppData\Roaming\uv\python\cpython-3.12.15-windows-x86_64-none\python.exe'
SEEDS = [42, 143, 244, 345, 446]
TARGETS = ['uptake', 'selectivity']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scope', choices=['mapped', 'full'], required=True)
    ap.add_argument('--concurrency', type=int, default=3)
    ap.add_argument('--protocols', default='random,LOTO')
    ap.add_argument('--models', default='')
    args = ap.parse_args()
    out = P / ('outputs_mf1_sensitivity_full' if args.scope == 'full' else 'outputs_mf1_sensitivity_mapped')
    out.mkdir(exist_ok=True)
    units = [(s, t) for s in SEEDS for t in TARGETS]
    if args.scope == 'mapped':
        units = [u for u in units if u != (42, 'uptake')]
    log = open(out / 'driver.log', 'a', encoding='utf-8')

    def note(msg):
        line = f'{datetime.datetime.now().isoformat()} {msg}'
        print(line, flush=True)
        log.write(line + '\n')
        log.flush()

    note(f'START scope={args.scope} conc={args.concurrency} protocols={args.protocols} units={len(units)}')
    running = []
    pending = list(units)
    while pending or running:
        while pending and len(running) < args.concurrency:
            s, t = pending.pop(0)
            cmd = [PY, str(P / 'scripts' / 'run_mf_setting.py'), '--scope', args.scope,
                   '--seeds', str(s), '--targets', t, '--protocols', args.protocols,
                   '--n-jobs', '1']
            if args.models:
                cmd += ['--models', args.models]
            o = open(out / f'proc_{t}_{s}.out', 'a', encoding='utf-8')
            e = open(out / f'proc_{t}_{s}.err', 'a', encoding='utf-8')
            proc = subprocess.Popen(cmd, cwd=str(P), stdout=o, stderr=e, stdin=subprocess.DEVNULL)
            running.append((proc, s, t, o, e))
            note(f'LAUNCH {args.scope} {t} {s} pid={proc.pid}')
        time.sleep(15)
        keep = []
        for proc, s, t, o, e in running:
            rc = proc.poll()
            if rc is None:
                keep.append((proc, s, t, o, e))
            else:
                o.close()
                e.close()
                note(f'EXIT {args.scope} {t} {s} rc={rc}')
        running = keep
    note(f'ALL DONE scope={args.scope}')
    log.close()


if __name__ == '__main__':
    main()
