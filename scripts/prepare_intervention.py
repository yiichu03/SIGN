#!/usr/bin/env python3
"""Freeze P1–P4 tasks/source/references; never submits a job."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys
from prepare_memory_four_arm import TREE, ROOT, sha, write


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output.resolve()
    subprocess.run([sys.executable,str(TREE/'scripts/prepare_memory_four_arm.py'),'--output',str(out)],check=True)
    old=ROOT/'logs/qwen_recovery_iteration_20261108/expanded_v2/expanded03_full'
    refs=dict(off=str(old/'full_off'),rule=str(old/'full_rule'),
        A=str(ROOT/'logs/qwen_memory_formal_20261108/formal_retry/full_A'),
        E2=str(ROOT/'logs/qwen_six_ablation_20261108/runtime_e9396ac/full_E2'),
        smoke_A=str(ROOT/'logs/qwen_six_ablation_20261108/runtime_e9396ac/checks/smoke_A'),
        smoke_rule=str(ROOT/'logs/qwen_memory_four_arm_20261108/smoke_057740b/smoke_rule'))
    write(out/'references.json',refs)
    manifest=json.loads((out/'source_manifest.json').read_text())
    assets=[out/'references.json',TREE/'docs/experiments/qwen-intervention-memory/PLAN.md',
        ROOT/'logs/qwen_memory_formal_20261108/launch_retry/prewarm.py']
    for folder in refs.values():
        d=Path(folder);assets += [d/'result.json']+list((d/'episodes').glob('*.jsonl'))
        assets += list((d/'native/recovery').glob('*.jsonl'))
    for f in assets:manifest['assets'][str(f)]=sha(f)
    write(out/'source_manifest.json',manifest)
    commands={}
    for arm in ['check','P1','P2','P3','P4']:
        cmd=['qsub','-q','autox','-P','CFP04-SF-109','-N','gate-'+arm,'-v',
            'GATE_TREE='+str(TREE)+',GATE_BATCH='+str(out)+',GATE_ARM='+arm,
            '-o',str(out/('pbs_'+arm+'.log')),str(TREE/'scripts/intervention.pbs')]
        if arm=='check':cmd[1:1]=['-l','walltime=02:00:00']
        commands[arm]=cmd
    write(out/'prepared_commands.json',dict(commit=manifest['commit'],submitted=False,commands=commands))
    (out/'formal_commands.sh').write_text('# Prepared, not submitted. P1-P4 require passed technical checks.\n'+
        '\n'.join(shlex.join(c) for c in commands.values())+'\n')


if __name__=='__main__':main()
