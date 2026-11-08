#!/usr/bin/env python3
"""Freeze inputs for the six single-factor checks; never submits a job."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from prepare_memory_four_arm import TREE, ROOT, sha, write


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output.resolve()
    subprocess.run([sys.executable,str(TREE/'scripts/prepare_memory_four_arm.py'),'--output',str(out)],check=True)
    source=ROOT/'logs/qwen_six_ablation_20261108/original_A_audit/decisions.json'
    records=json.loads(source.read_text());assert len(records)==155
    write(out/'original_A_decisions.json',records)
    refs=dict(A=str(ROOT/'logs/qwen_memory_formal_20261108/formal_retry/full_A'),
        rule=str(ROOT/'logs/qwen_recovery_iteration_20261108/expanded_v2/expanded03_full/full_rule'),
        smoke_A=str(ROOT/'logs/qwen_memory_four_arm_20261108/smoke_057740b/smoke_A'))
    write(out/'six_references.json',refs)
    manifest=json.loads((out/'source_manifest.json').read_text())
    assets=[source,out/'original_A_decisions.json',out/'six_references.json',TREE/'docs/experiments/qwen-six-ablation/PLAN.md',
        ROOT/'logs/qwen_memory_formal_20261108/launch_retry/prewarm.py']
    assets += [Path(i['image']) for r in records for i in r['request']['images']]
    for ref in refs.values():
        b=Path(ref);assets += [b/'result.json']+list((b/'episodes').glob('*.jsonl'))
        assets += list((b/'native/recovery').glob('*.jsonl'))
    for path in assets:manifest['assets'][str(path)]=sha(path)
    write(out/'source_manifest.json',manifest)
    # Parent commands are only a preparation artifact, never run here.
    commands={arm:'qsub -q autox -P CFP04-SF-109 -N six-'+arm+' -v SIX_TREE='+str(TREE)+',SIX_BATCH='+str(out)+',SIX_ARM='+arm+
        ' -o '+str(out/('pbs_'+arm+'.log'))+' '+str(TREE/'scripts/six_ablation.pbs') for arm in ['E1','E2','E3','E4','E5','E6']}
    commands['check']='qsub -q autox -P CFP04-SF-109 -N six-check -v SIX_TREE='+str(TREE)+',SIX_BATCH='+str(out)+',SIX_ARM=check -o '+str(out/'pbs_check.log')+' '+str(TREE/'scripts/six_ablation.pbs')
    write(out/'prepared_commands.json',dict(commit=manifest['commit'],submitted=False,commands=commands))
    (out/'formal_commands.sh').write_text('# Prepared only. Formal E jobs require checks/check_summary.json passed.\n'+'\n'.join(commands.values())+'\n')


if __name__=='__main__':main()
