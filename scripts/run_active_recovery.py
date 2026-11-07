#!/usr/bin/env python3
"""Native equivalence, real view diagnostics, then a bounded four-arm screen."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import statistics
TREE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(TREE/'scripts'))
from evaluate_recovery import guard,read_rows


def run(batch,name,split,mode,native=False,active=True):
    out=batch/name
    command=[sys.executable,str(TREE/'scripts/evaluate_recovery.py'),'--batch',str(batch),'--run',str(out),
        '--split',split,'--mode',mode]
    if active:command.append('--active')
    env=dict(os.environ)
    if native:env['RECOVERY_NATIVE_REFERENCE']='1'
    else:env.pop('RECOVERY_NATIVE_REFERENCE',None)
    print('RUN',json.dumps(command),flush=True)
    with (batch/(name+'.log')).open('x') as f:subprocess.run(command,env=env,cwd=TREE,stdout=f,stderr=subprocess.STDOUT,check=True)
    return out


def audit_views(folder):
    events=folder/'native/recovery/events.jsonl'
    if not events.exists():return 0
    import hashlib
    for r in map(json.loads,events.read_text().splitlines()):
        assert r['decision_step']-r['step']==12
        assert r['view_steps']==dict(left=r['step']+3,right=r['step']+9,forward=r['step']+12)
        assert r['survey_command_steps']==12
        for f in r['view_files'].values():assert hashlib.sha256(Path(f['path']).read_bytes()).hexdigest()==f['sha256']
    return len(events.read_text().splitlines())


def main():
    p=argparse.ArgumentParser();p.add_argument('--batch',type=Path,required=True);a=p.parse_args();batch=a.batch.resolve()
    guard(batch)
    native=run(batch,'dev_native','smoke','off',True)
    off=run(batch,'dev_off','smoke','off')
    disabled=run(batch,'dev_disabled','smoke','disabled')
    assert read_rows(native/'episodes')==read_rows(off/'episodes')==read_rows(disabled/'episodes')
    scan=run(batch,'dev_scan','smoke','scan')
    count=audit_views(scan)
    # Ground-truth telemetry below is QA only; never an input to the supervisor.
    import numpy as np
    import math
    view_checks=[]
    event_path=scan/'native/recovery/events.jsonl'
    if event_path.exists():
        for event in map(json.loads,event_path.read_text().splitlines()):
            scene=Path(event['episode'][0]).stem;episode=event['episode'][1];start=event['step']
            with np.load(scan/'audit_traces'/(scene+'_'+episode+'.npz'),allow_pickle=False) as trace:
                poses=trace['poses'];commands=trace['commands']
                expected=np.array([[-1.,w] for w in [1]*3+[-1]*6+[1]*3],dtype=np.float32)
                assert np.array_equal(commands[start:start+12],expected)
                positions=poses[start:start+13,:3]
                drift=float(np.linalg.norm(positions-positions[0],axis=1).max());assert drift<1e-4
                def yaw(q):
                    x,y,z,w=map(float,q);return math.degrees(math.atan2(2*(w*y+x*z),1-2*(y*y+z*z)))
                origin=yaw(poses[start,3:]);deltas=[]
                for offset,target in [(3,45),(9,-45),(12,0)]:
                    delta=(yaw(poses[start+offset,3:])-origin+180)%360-180
                    assert abs(delta-target)<.01,(delta,target)
                    deltas.append(delta)
                view_checks.append(dict(id=event['id'],position_drift_m=drift,relative_yaws=deltas))
    (batch/'view_capture_audit.json').write_text(json.dumps(dict(passed=True,completed_surveys=count,checks=view_checks,
        note='Sim poses are passive QA only, never controller/VLM inputs'),indent=2)+'\n')
    if not count:
        (batch/'diagnosis.json').write_text(json.dumps(dict(status='no_completed_views',full_submitted=False))+'\n');return
    env=dict(os.environ);env.pop('PYTHONPATH',None);env.pop('PYTHONHOME',None);env['PYTHONNOUSERSITE']='1'
    command=['/scratch/e1538633/liuyi/envs/qwen35/bin/python',str(TREE/'scripts/diagnose_active_recovery.py'),
        '--events',str(scan/'native/recovery/events.jsonl'),'--output',str(batch/'offline')]
    with (batch/'offline.log').open('x') as f:subprocess.run(command,env=env,cwd=TREE,stdout=f,stderr=subprocess.STDOUT,check=True)
    diagnostic=json.loads((batch/'offline/summary.json').read_text());assert diagnostic['technical_passed']
    if not diagnostic['balanced_has_directional_choice']:
        (batch/'diagnosis.json').write_text(json.dumps(dict(status='still_all_C_on_development',diagnostic=diagnostic,
            note='No forced labels or extra navigation jobs; inspect evidence and explanations before changing design again.'),indent=2)+'\n');return
    folders={}
    for mode in ['off','scan','rule','qwen']:
        folders[mode]=run(batch,'confirm_'+mode,'pilot',mode)
        if mode!='off':audit_views(folders[mode])
    results={m:json.loads((f/'result.json').read_text()) for m,f in folders.items()}
    records={m:read_rows(f/'episodes') for m,f in folders.items()};baseline=records['off'];paired={};per_scene=[];paired_rows=[]
    for mode,rows in records.items():
        assert set(rows)==set(baseline) and len(rows)==280
        for k,r in rows.items():assert r['goal_sha256']==baseline[k]['goal_sha256'] and r['start_position']==baseline[k]['start_position']
        if mode!='off':
            interventions={tuple(r['episode']):r for r in map(json.loads,
                (folders[mode]/'native/recovery/episodes.jsonl').read_text().splitlines())}
            paired[mode]=dict(failure_to_success=sum(bool(r['success']) and not baseline[k]['success'] for k,r in rows.items()),
                success_to_failure=sum(bool(baseline[k]['success']) and not r['success'] for k,r in rows.items()),
                sr_delta_pp=100*(results[mode]['success_rate']-results['off']['success_rate']),
                spl_delta_pp=100*(results[mode]['spl']-results['off']['spl']),
                success_changes_without_any_override=sum(r['success']!=baseline[k]['success'] and not interventions[k]['overrides'] for k,r in rows.items()),
                success_changes_without_selected_recovery=sum(r['success']!=baseline[k]['success'] and not interventions[k]['recovery_steps'] for k,r in rows.items()))
            for key,r in sorted(rows.items()):
                h=interventions[key]
                paired_rows.append(dict(mode=mode,scene_id=key[0],episode_id=key[1],
                    off_success=baseline[key]['success'],success=r['success'],off_spl=baseline[key]['spl'],spl=r['spl'],
                    survey_steps=h['survey_steps'],recovery_steps=h['recovery_steps'],
                    human_category='',human_notes=''))
        for scene in sorted({k[0] for k in rows}):
            data=[r for k,r in rows.items() if k[0]==scene]
            per_scene.append(dict(mode=mode,scene_id=scene,episodes=len(data),sr=statistics.mean(r['success'] for r in data),spl=statistics.mean(r['spl'] for r in data)))
    summary=dict(passed=True,cases=results,paired=paired,offline=diagnostic,
        note='Fixed fresh 280-task confirmation inside reused Gibson val. Compare qwen with scan and rule; scanning actions are not Qwen-selected recoveries. Small sample, no significance or human-cause claims.',full_submitted=False)
    import csv
    with (batch/'per_scene.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(per_scene[0]));w.writeheader();w.writerows(per_scene)
    with (batch/'paired_tasks.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(paired_rows[0]));w.writeheader();w.writerows(paired_rows)
    (batch/'comparison.json').write_text(json.dumps(summary,indent=2)+'\n')
    guard(batch);print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
