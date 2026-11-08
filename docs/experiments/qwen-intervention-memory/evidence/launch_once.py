"""One authorized batch: retry unavailable scheduler, then check, then four jobs."""
import datetime, json, os, pwd, subprocess, time
from pathlib import Path
ROOT=Path('/scratch/e1538633/liuyi')
BATCH=ROOT/'logs/qwen_intervention_memory_20261109/runtime_8a94adf'
TREE=ROOT/'SIGN-qwen-intervention-runtime-8a94adf'
COMMAND=json.loads((BATCH/'prepared_commands.json').read_text())['commands']['check']
STATE=BATCH/'launch_state.json'
def update(phase,**extra):
    value=dict(time=datetime.datetime.now().astimezone().isoformat(),pid=os.getpid(),phase=phase,**extra)
    STATE.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value),flush=True)
def run(cmd,timeout=60):
    return subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
def main():
    if (BATCH/'formal_submissions.json').exists():
        update('already_submitted');return
    while not (BATCH/'check_submission.json').exists():
        if (BATCH/'STOP_LAUNCH').exists():update('stopped_by_user');return
        try:
            name=pwd.getpwuid(os.getuid()).pw_name
            if name!='e1538633':raise RuntimeError('Unexpected local account '+name)
            status=run(['qstat','-u','e1538633'],30)
            if status.returncode:
                update('waiting_scheduler',error=status.stderr.strip());time.sleep(45);continue
            result=run(COMMAND,60)
            record=dict(time=datetime.datetime.now().astimezone().isoformat(),command=COMMAND,
                returncode=result.returncode,stdout=result.stdout,stderr=result.stderr)
            with (BATCH/'check_submission_attempts.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
            if result.returncode==0:
                record['job_id']=result.stdout.strip()
                if not record['job_id'].split('.')[0].isdigit():raise RuntimeError('Ambiguous qsub result; manual inspection required')
                (BATCH/'check_submission.json').write_text(json.dumps(record,indent=2)+'\n')
                update('gpu_check_submitted',job_id=record['job_id'])
            elif not result.stdout.strip() and 'cannot connect to server' in result.stderr:
                update('waiting_scheduler',error=result.stderr.strip());time.sleep(45)
            else:raise RuntimeError('Submission rejected; no automatic repeat: '+result.stderr)
        except KeyError:
            update('waiting_local_account_lookup',uid=os.getuid());time.sleep(45)
    job=json.loads((BATCH/'check_submission.json').read_text())['job_id']
    while not (BATCH/'checks/check_summary.json').exists():
        if (BATCH/'STOP_LAUNCH').exists():update('stopped_by_user',check_job=job);return
        result=run(['qstat','-fx','-F','json',job],40)
        if result.returncode==0:
            jobs=json.loads(result.stdout)['Jobs'];state=next(iter(jobs.values()))
            if state.get('job_state')=='F':raise RuntimeError('GPU check ended without passed summary; no formal submission: '+str(state.get('Exit_status')))
            update('waiting_gpu_check',job_id=job,job_state=state.get('job_state'))
        else:update('waiting_check_status',job_id=job,error=result.stderr.strip())
        time.sleep(45)
    check=json.loads((BATCH/'checks/check_summary.json').read_text())
    if not check['passed']:raise RuntimeError('GPU check failed; no formal submission')
    if (BATCH/'STOP_LAUNCH').exists():update('stopped_by_user',check_job=job);return
    update('submitting_formal',check_job=job)
    result=run([str(ROOT/'envs/sign-baseline/bin/python'),str(TREE/'scripts/submit_intervention.py'),'--batch',str(BATCH)],180)
    (BATCH/'formal_submit_console.txt').write_text(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError('Formal submit stopped; inspect receipt before retry: '+result.stderr)
    update('formal_submitted',receipt=json.loads((BATCH/'formal_submissions.json').read_text()))
if __name__=='__main__':
    try:main()
    except Exception as exc:
        update('needs_inspection',error=str(exc));raise
