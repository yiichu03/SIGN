#!/usr/bin/env python3
"""Candidate diagnostics and a fixed three-arm confirmation, with native controls."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
TREE=Path(__file__).resolve().parents[1]
from run_active_recovery import run, summarize, audit_views
from evaluate_recovery import guard, read_rows


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--batch',type=Path,required=True)
    batch=parser.parse_args().batch.resolve();guard(batch)
    command=[sys.executable,str(TREE/'scripts/diagnose_candidate_recovery.py'),
        '--events',json.loads((batch/'candidate_inputs.json').read_text())['source_events'],
        '--output',str(batch/'offline')]
    with (batch/'offline.log').open('x') as f:
        subprocess.run(command,cwd=TREE,stdout=f,stderr=subprocess.STDOUT,check=True)
    diagnostic=json.loads((batch/'offline/summary.json').read_text());assert diagnostic['technical_passed']
    paths=[]
    for name,mode,native in [('smoke_native','off',True),('smoke_off','off',False),('smoke_disabled','disabled',False)]:
        paths.append(run(batch,name,'smoke',mode,native=native,candidate=True))
    assert read_rows(paths[0]/'episodes')==read_rows(paths[1]/'episodes')==read_rows(paths[2]/'episodes')
    (batch/'technical_gate.json').write_text(json.dumps(dict(passed=True,
        native_off_zero_intervention_exact=True,diagnostic=diagnostic),indent=2)+'\n')
    folders={}
    for mode in ['off','rule','qwen']:
        folders[mode]=run(batch,'confirm_'+mode,'pilot',mode,candidate=True)
        if mode!='off':audit_views(folders[mode])
    summarize(batch,folders,diagnostic)


if __name__=='__main__':main()
