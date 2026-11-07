"""Submit verified continuations once, within each original 168h budget."""
import json
from pathlib import Path
import subprocess
from datetime import datetime, timedelta, timezone

HERE=Path(__file__).resolve().parent
plan=json.loads((HERE/'plan.json').read_text())
short=json.loads((HERE/'short_submission.json').read_text())
status=json.loads(subprocess.check_output(['qstat','-fx','-F','json',short['job_id']],text=True))['Jobs'][short['job_id']]
assert status['job_state']=='F' and status['Exit_status']==0
for name in plan:assert json.loads((HERE/name/'short_validation.json').read_text())['passed']
record_path=HERE/'formal_submission.json'
assert not record_path.exists(),'Submission already recorded; inspect before retrying'
records={'short_job':short['job_id'],'cases':{},
         'budget_rule':'Each formal walltime = original168h - previousPBSused - 1h reserved verification. This is a conservative cap; 1h is not claimed actual consumption.',
         'legacy_resume_caveat':'All model weights/counters restored; optimizer/episodes/RNG reset. Not an exact trajectory resume.'}
record_path.write_text(json.dumps(records,indent=2)+'\n')
# Respect the earlier A/C preference; B may wait for GPUx max_run slots.
for case in ['A','C','qwen01','coverage256','coverage32','B']:
    p=plan[case];seconds=p['remaining_budget_seconds']-3600
    assert 0<seconds<=168*3600
    walltime=f'{seconds//3600:02d}:{seconds%3600//60:02d}:{seconds%60:02d}'
    command=['qsub','-N','cont-'+{'coverage256':'cov256','coverage32':'cov32'}.get(case,case),
        '-l','walltime='+walltime,'-o',str(HERE/case/'train.pbs.log'),'-v','CONT_CASE='+case,str(HERE/'formal.pbs')]
    result=subprocess.run(command,capture_output=True,text=True)
    if result.returncode:
        records['submission_error']={'case':case,'command':command,'stdout':result.stdout,'stderr':result.stderr}
        record_path.write_text(json.dumps(records,indent=2)+'\n')
        raise RuntimeError(result.stderr)
    item=dict(job_id=result.stdout.strip(),command=command,walltime=walltime,
        old_used_seconds=p['old_used_seconds'],verification_reserve_seconds=3600,
        formal_max_seconds=seconds,cumulative_start_step=p['start_step'],
        output=str(Path(p['tree'])/'results/continuation_20261103'/case/'train'),
        submitted_at=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'))
    records['cases'][case]=item
    record_path.write_text(json.dumps(records,indent=2)+'\n')
    print(case,item['job_id'],walltime,flush=True)
