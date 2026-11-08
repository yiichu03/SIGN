from pathlib import Path
import hashlib,json,subprocess
import numpy as np
ROOT=Path('/scratch/e1538633/liuyi');B=ROOT/'logs/qwen_memory_four_arm_20261108/smoke_057740b'
summary=json.loads((B/'smoke_summary.json').read_text());assert summary['passed']
read=lambda p:[json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []
get=lambda folder:{(r['scene_id'],r['episode_id']):r for p in (folder/'episodes').glob('*.jsonl') for r in read(p)}
native=get(B/'smoke_native');review={}
for arm in ['native','off','disabled','rule','A','B','C','D']:
 folder=B/('smoke_'+arm);rows=get(folder);assert set(rows)==set(native)
 if arm in ['off','disabled']:
  for key,r in rows.items():
   for k in ['success','spl','view_match','navigation_reward','collisions','steps','pose_trace_sha256','actual_actions_sha256']:assert r[k]==native[key][k]
 controller=folder/'native/recovery';stats=read(controller/'episodes.jsonl')
 for r in stats:
  key=tuple(r['episode']);assert r['steps']==rows[key]['steps']
  assert r['actions_sha256']==rows[key]['actual_actions_sha256'];assert r['overrides']<=76
  name=Path(key[0]).stem+'_'+key[1]+'.npz'
  with np.load(folder/'audit_traces'/name,allow_pickle=False) as trace:
   assert len(trace['commands'])==r['steps'];assert len(trace['poses'])==r['steps']+1
   assert hashlib.sha256(trace['commands'].astype('float32').tobytes()).hexdigest()==r['actions_sha256']
 events=read(controller/'events.jsonl');feedback=read(controller/'feedback.jsonl');verified_fb=0
 for row in feedback:
  if 'choice' not in row:continue
  episode=tuple(row['episode']);event=next(e for e in events if e['id']+':feedback'==row['id'])
  t=row['step'];assert t==event['decision_step']+10
  with np.load(folder/'audit_traces'/(Path(episode[0]).stem+'_'+episode[1]+'.npz'),allow_pickle=False) as trace:
   np.testing.assert_allclose(trace['commands'][t-4:t],row['actual_commands'],atol=1e-7,rtol=0)
   assert np.all(trace['commands'][t-4:t,1]==0)
   assert abs(np.dot(trace['poses'][t-4,3:],trace['poses'][t,3:]))>1-1e-6
  verified_fb+=1
 for e in events:
  request=e.get('request')
  if request:
   assert [r['role'] for r in request['images'][:4]]==['GOAL','CURRENT','LEFT','RIGHT']
   for image in request['images']:assert hashlib.sha256(Path(image['image']).read_bytes()).hexdigest()==image['image_sha256']
 for p in (controller/'worker').glob('request*.json'):
  d=json.loads(p.read_text());assert all(r['valid'] for r in d['results'])
 review[arm]=dict(episodes=len(rows),attempts=sum(r['attempts'] for r in stats),verified_same_heading_feedback=verified_fb,
  memory_writes=sum(r.get('memory_stats',{}).get('writes',0) for r in stats),
  memory_hits=sum(r.get('memory_hits',0) for r in stats),memory_changed=sum(r.get('memory_changed_decisions',0) for r in stats),
  technical_error_files=list(map(str,controller.glob('technical_errors.jsonl'))))
 assert not review[arm]['technical_error_files']
job=json.loads(subprocess.check_output(['qstat','-fx','-F','json','1532823'],text=True))['Jobs']['1532823.stdct-mgmt-02']
assert job['job_state']=='F' and job['Exit_status']==0
out=dict(passed=True,job_id='1532823.stdct-mgmt-02',walltime=job['resources_used']['walltime'],runtime_commit='057740b7ac57ec9342459920fb5263cc18b03084',
 exact_native_off_disabled=True,all_real_action_sha_match=True,all_real_feedback_four_commands_and_pose_heading_match=True,arms=review,
 limitation='12 purposive engineering episodes; no formal SR evidence. Zero online verified memory hits in C/D. Final change only persists technical_errors/agent_variant in summary, checked by CPU regression.')
(ROOT/'logs/qwen_memory_four_arm_20261108/review_smoke.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
