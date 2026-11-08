#!/usr/bin/env python3
"""Explicitly submit one verified P1–P4 batch and its dependent CPU report."""
import argparse
from datetime import datetime,timezone,timedelta
import hashlib
import json
from pathlib import Path
import subprocess
TREE=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--batch',type=Path,required=True);a=p.parse_args();b=a.batch.resolve()
    manifest=json.loads((b/'source_manifest.json').read_text());check=json.loads((b/'checks/check_summary.json').read_text())
    assert check['passed'] and check['source_commit']==manifest['commit']
    assert subprocess.check_output(['git','-C',str(TREE),'rev-parse','HEAD'],text=True).strip()==manifest['commit']
    for f,digest in manifest['files'].items():assert hashlib.sha256((TREE/f).read_bytes()).hexdigest()==digest,f
    for f,digest in manifest['assets'].items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==digest,f
    receipt=b/'formal_submissions.json';assert not receipt.exists(),'Existing receipt: do not duplicate jobs'
    commands=json.loads((b/'prepared_commands.json').read_text())['commands'];jobs={}
    record=dict(submitted_at=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
        source_commit=manifest['commit'],jobs=jobs,gate_sha256=hashlib.sha256((b/'checks/check_summary.json').read_bytes()).hexdigest())
    for arm in ['P1','P2','P3','P4']:
        assert not (b/('full_'+arm)).exists()
        run=subprocess.run(commands[arm],text=True,capture_output=True,check=True);job=run.stdout.strip()
        assert job.split('.')[0].isdigit(),(job,run.stderr)
        jobs[arm]=dict(job_id=job,command=commands[arm],source_commit=manifest['commit'],output=str(b/('full_'+arm)))
        receipt.write_text(json.dumps(record,indent=2)+'\n');print(arm,job,flush=True)
    cmd=['qsub','-q','autox','-P','CFP04-SF-109','-W','depend=afterany:'+':'.join(j['job_id'] for j in jobs.values()),
        '-v','GATE_TREE='+str(TREE)+',GATE_BATCH='+str(b),'-o',str(b/'pbs_report.log'),str(TREE/'scripts/intervention_report.pbs')]
    run=subprocess.run(cmd,text=True,capture_output=True,check=True)
    record['report']=dict(job_id=run.stdout.strip(),command=cmd,output=str(b/'formal_review'))
    receipt.write_text(json.dumps(record,indent=2)+'\n');print('report',run.stdout.strip(),flush=True)


if __name__=='__main__':main()
