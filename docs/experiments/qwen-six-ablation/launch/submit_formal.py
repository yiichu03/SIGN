"""Submit only after frozen engineering gate; preserve receipts, no retries."""
import hashlib,json,os,subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path('/scratch/e1538633/liuyi')
BATCH=ROOT/'logs/qwen_six_ablation_20261108/runtime_e9396ac'
TREE=ROOT/'SIGN-qwen-six-runtime-e9396ac'
EXPECTED='e9396ac0c989ea515edcbd7f8d0085be38f818e7'
def main():
    manifest=json.loads((BATCH/'source_manifest.json').read_text());check=json.loads((BATCH/'checks/check_summary.json').read_text())
    assert check['passed'] and check['source_commit']==EXPECTED==manifest['commit']
    assert subprocess.check_output(['git','-C',str(TREE),'rev-parse','HEAD'],text=True).strip()==EXPECTED
    assert json.loads((BATCH/'offline/summary.json').read_text())['passed']
    for path,digest in manifest['files'].items():assert hashlib.sha256((TREE/path).read_bytes()).hexdigest()==digest,path
    for path,digest in manifest['assets'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
    receipt=BATCH/'formal_submissions.json';assert not receipt.exists(),'Do not duplicate formal submissions'
    commands=json.loads((BATCH/'prepared_commands.json').read_text())['commands'];jobs={}
    for arm in ['E1','E2','E3','E4','E5','E6']:
        assert not (BATCH/('full_'+arm)).exists()
        r=subprocess.run(commands[arm],shell=True,text=True,capture_output=True);r.check_returncode();job=r.stdout.strip()
        assert job.split('.')[0].isdigit(),(job,r.stderr)
        jobs[arm]=dict(job_id=job,command=commands[arm],output=str(BATCH/('full_'+arm)),source_commit=EXPECTED)
        receipt.write_text(json.dumps(dict(submitted_at=datetime.now(ZoneInfo('Asia/Singapore')).isoformat(timespec='seconds'),
            source_commit=EXPECTED,gate_sha256=hashlib.sha256((BATCH/'checks/check_summary.json').read_bytes()).hexdigest(),
            jobs=jobs,all_six_submitted=len(jobs)==6),indent=2)+'\n')
        print(arm,job,flush=True)
if __name__=='__main__':main()
