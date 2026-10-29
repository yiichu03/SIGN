"""Submit one fresh formal train plus two milestone-gated original-protocol evals."""
import datetime,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent

def now():return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='seconds')
def submit(command):
    print('SUBMIT',command,flush=True)
    job=subprocess.check_output(command,text=True).strip();assert job.endswith('.stdct-mgmt-02'),job
    return dict(job_id=job,command=command,submitted_at=now())

def main():
    from run_training import guard
    guard()
    for name in ['short_validation.json','config_audit.json','offline_online_geometry.json','addressing_validation.json','watcher_validation.json','milestone_validation.json','eval_config_validation.json']:
        assert json.loads((HERE/name).read_text())['passed'],name
    assert not (HERE/'submission.json').exists(),'Do not duplicate formal submission'
    state={'runtime_commit':json.loads((HERE/'source_manifest.json').read_text())['trees']['SIGN-qwen128-reward']['commit'],'evaluations':{}}
    # Persist each receipt immediately; inspect existing receipts after any interrupted submission.
    state['training']=submit(['qsub',str(HERE/'formal.pbs')]);(HERE/'submission.json').write_text(json.dumps(state,indent=2)+'\n')
    train=state['training']['job_id']
    for step in (4608000,8192000):
        out=HERE/f'val_{step}';out.mkdir(exist_ok=False)
        wait=submit(['qsub','-N',f'qwen-wait-{step}','-o',str(out/'wait.pbs.log'),'-v',f'QWEN_TRAIN_JOB={train},QWEN_EVAL_STEP={step}',
                     '-W',f'depend=after:{train}',str(HERE/'watch.pbs')])
        state['evaluations'][str(step)]={'wait':wait};(HERE/'submission.json').write_text(json.dumps(state,indent=2)+'\n')
        evaluation=submit(['qsub','-N',f'qwen-val-{step}','-o',str(out/'evaluate.pbs.log'),'-v',f'QWEN_EVAL_STEP={step}',
                           '-W',f"depend=afterok:{wait['job_id']}",str(HERE/'evaluate.pbs')])
        state['evaluations'][str(step)]['evaluation']=evaluation
        (out/'submission.json').write_text(json.dumps(state['evaluations'][str(step)],indent=2)+'\n')
        (HERE/'submission.json').write_text(json.dumps(state,indent=2)+'\n')
    print(json.dumps(state,indent=2))
if __name__=='__main__':main()
