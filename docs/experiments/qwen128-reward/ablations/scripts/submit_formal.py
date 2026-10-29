"""One fresh formal job per case; preserve original training and dependency jobs."""
import datetime,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent

def now():return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='seconds')
def submit(command):
    print('SUBMIT',command,flush=True)
    job=subprocess.check_output(command,text=True).strip();assert job.endswith('.stdct-mgmt-02'),job
    return dict(job_id=job,command=command,submitted_at=now())
def main():
    from run_case import guard
    guard();assert json.loads((HERE/'config_audit.json').read_text())['passed']
    for case in ['A','C','B']:assert json.loads((HERE/case/'short_validation.json').read_text())['passed'],case
    assert not (HERE/'formal_submission.json').exists(),'Inspect existing receipts; never repeat formal submission'
    state={'runtime_commit':json.loads((HERE/'source_manifest.json').read_text())['trees']['SIGN-qwen-ablation']['commit'],'cases':{}}
    def save():(HERE/'formal_submission.json').write_text(json.dumps(state,indent=2)+'\n')
    # A/C are submitted first; B naturally waits if the scheduler has fewer free slots.
    for case in ['A','C','B']:
        out=HERE/case;record={'evaluations':{}};state['cases'][case]=record
        record['training']=submit(['qsub','-N','abc-'+case+'-formal','-o',str(out/'formal.pbs.log'),'-v','ABC_CASE='+case,str(HERE/'formal.pbs')]);save()
    for case in ['A','C','B']:
        out=HERE/case;record=state['cases'][case];train=record['training']['job_id']
        for step in (4608000,8192000):
            target=out/f'val_{step}';target.mkdir(exist_ok=False)
            wait=submit(['qsub','-N',f'abc-{case}-w{step}','-o',str(target/'wait.pbs.log'),'-v',f'ABC_TRAIN_JOB={train},ABC_EVAL_STEP={step},ABC_CASE={case}',
                         '-W',f'depend=after:{train}',str(HERE/'watch.pbs')])
            record['evaluations'][str(step)]={'wait':wait};save()
            evaluation=submit(['qsub','-N',f'abc-{case}-v{step}','-o',str(target/'evaluate.pbs.log'),'-v',f'ABC_EVAL_STEP={step},ABC_CASE={case}',
                               '-W',f"depend=afterok:{wait['job_id']}",str(HERE/'evaluate.pbs')])
            record['evaluations'][str(step)]['evaluation']=evaluation
            (target/'submission.json').write_text(json.dumps(record['evaluations'][str(step)],indent=2)+'\n');save()
    print(json.dumps(state,indent=2))
if __name__=='__main__':main()
