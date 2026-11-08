"""Finite follow-through: development -> repeat -> untouched confirmation -> full."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
ROOT=Path('/scratch/e1538633/liuyi')
HERE=Path(__file__).resolve().parent


def record(path,item):
    item['recorded_at']=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='seconds')
    path.write_text(json.dumps(item,indent=2)+'\n')
    with (ROOT/'WORKLOG.md').open('a') as f:
        f.write('\n\n## '+item['recorded_at']+' [QWEN-ITERATION-AUTOMATIC-RECEIPT]\n\n- '+json.dumps(item,ensure_ascii=False)+'\n')


def main():
    p=argparse.ArgumentParser();p.add_argument('--round',required=True);p.add_argument('--phase',choices=['develop','repeat','confirm','full'],required=True);p.add_argument('--job',required=True);a=p.parse_args()
    for name,digest in json.loads((HERE/'orchestration_manifest.json').read_text()).items():
        assert hashlib.sha256((HERE/name).read_bytes()).hexdigest()==digest,name
    suffix={'develop':'','repeat':'_repeat','confirm':'_confirmation','full':'_full'}[a.phase]
    batch=HERE/(a.round+suffix);receipt=batch/'dispatch.json'
    if receipt.exists():return
    submitted=json.loads((batch/'submission.json').read_text())
    jobs=json.loads(subprocess.check_output(['qstat','-fx','-F','json',a.job],text=True))['Jobs'];status=next(iter(jobs.values()))
    if status['job_state']!='F' or status.get('Exit_status')!=0:
        record(receipt,dict(status='requires_revision',phase=a.phase,job=a.job,reason='Upstream job did not finish Exit0',pbs_state=status['job_state'],exit=status.get('Exit_status')));return
    result=json.loads((batch/'iteration_result.json').read_text());assert result['technical_passed']
    for split,comparison in result['comparisons'].items():
        records={}
        for mode,case in comparison['cases'].items():
            assert case['source_commit']==submitted['commit'] and case['training_step']==125952000
            rows={}
            for path in (batch/(split+'_'+mode)/'episodes').glob('*.jsonl'):
                for line in path.read_text().splitlines():
                    row=json.loads(line);key=(row['scene_id'],row['episode_id']);assert key not in rows;rows[key]=row
            assert len(rows)==case['episodes']
            assert abs(statistics.mean(v['success'] for v in rows.values())-case['success_rate'])<1e-12
            assert abs(statistics.mean(v['spl'] for v in rows.values())-case['spl'])<1e-12
            records[mode]=rows
        assert records['rule'].keys()==records['qwen'].keys()
        for key,row in records['qwen'].items():assert row['goal_sha256']==records['rule'][key]['goal_sha256'] and row['start_position']==records['rule'][key]['start_position']
    brief={s:dict(net=v['net_successes'],prefix_supported=v['supported_rescues'],sr_delta=v['sr_delta_pp'],spl_delta=v['spl_delta_pp']) for s,v in result['comparisons'].items()}
    if a.phase=='full':
        record(receipt,dict(status='full_completed',job=a.job,commit=submitted['commit'],comparisons=brief));return
    if not result['passes_fixed_gain_gate']:
        record(receipt,dict(status='requires_revision',phase=a.phase,job=a.job,commit=submitted['commit'],comparisons=brief,
            reason='Frozen gain/safety/prefix gate not met; no GPU follow-up submitted.'));return
    next_phase={'develop':'repeat','repeat':'confirm','confirm':'full'}[a.phase]
    next_round=a.round+'_repeat' if next_phase=='repeat' else a.round
    next_stage='development' if next_phase=='repeat' else 'confirmation' if next_phase=='confirm' else 'full'
    args=[sys.executable,str(HERE/'submit_iteration.py'),'--round',next_round,'--stage',next_stage,
        '--commit',submitted['commit'],'--profile',submitted['profile']]
    completed=subprocess.run(args,text=True,capture_output=True)
    (batch/'followup_submission.log').write_text(completed.stdout+completed.stderr);completed.check_returncode()
    next_batch=HERE/(a.round+{'repeat':'_repeat','confirm':'_confirmation','full':'_full'}[next_phase])
    follow=json.loads((next_batch/'submission.json').read_text())
    post=['qsub','-q','auto','-P','CFP04-SF-109','-W','depend=afterany:'+follow['job_id'],
        '-v','ITERATION_ROUND='+a.round+',ITERATION_PHASE='+next_phase+',ITERATION_JOB='+follow['job_id']+',ITERATION_CONTROL_DIR='+str(HERE),
        '-o',str(next_batch/'dispatch.pbs.log'),str(HERE/'dispatch_iteration.pbs')]
    p=subprocess.run(post,text=True,capture_output=True)
    record(receipt,dict(status=next_phase+'_submitted',job=a.job,commit=submitted['commit'],comparisons=brief,
        followup_job=follow['job_id'],followup_stage=next_stage,followup_batch=str(next_batch),
        cpu_dispatch_command=post,cpu_dispatch_returncode=p.returncode,cpu_dispatch_stdout=p.stdout,cpu_dispatch_stderr=p.stderr))
    p.check_returncode()


if __name__=='__main__':main()
