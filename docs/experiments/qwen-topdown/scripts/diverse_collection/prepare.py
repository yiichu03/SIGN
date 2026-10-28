from pathlib import Path
import json,gzip,hashlib,subprocess
ROOT=Path('/scratch/e1538633/liuyi');HERE=Path(__file__).resolve().parent
source=ROOT/'SIGN/data/datasets/imagenav/gibson/v1/val/val.json.gz';dataset=json.loads(gzip.decompress(source.read_bytes()))
scenes=['Cantwell','Eastville','Elmira','Eudora','Greigsville','Pablo','Ribera','Swormville']
groups=[]
for number,(lo,hi) in enumerate([(5,8),(8,15)],1):
 group={'id':'group_%02d'%number,'selection_distance_m':[lo,hi],'cases':[]}
 for index,scene in enumerate(scenes,1):
  candidates=[e for e in dataset['episodes'] if Path(e['scene_id']).stem==scene and lo<=e['info']['geodesic_distance']<hi and abs(e['start_position'][1]-e['goals'][0]['position'][1])<.05]
  if not candidates and number==2:
   first=groups[0]['cases'][index-1]['episode_id']
   candidates=sorted([e for e in dataset['episodes'] if Path(e['scene_id']).stem==scene and 5<=e['info']['geodesic_distance']<15 and abs(e['start_position'][1]-e['goals'][0]['position'][1])<.05 and str(e['episode_id'])!=first],key=lambda e:-e['info']['geodesic_distance'])
  assert candidates,(scene,lo,hi)
  episode=candidates[0];folder=HERE/group['id']/('C%02d'%index);folder.mkdir(parents=True,exist_ok=True)
  payload=dict(dataset,episodes=[episode])
  if (folder/'task.json.gz').exists():
   assert json.loads(gzip.decompress((folder/'task.json.gz').read_bytes()))==payload
  else:
   with gzip.open(folder/'task.json.gz','wt') as f:json.dump(payload,f)
  group['cases'].append({'id':folder.name,'scene':scene,'episode_id':str(episode['episode_id']),'geodesic_distance':episode['info']['geodesic_distance']})
 groups.append(group)
assert len({(c['scene'],c['episode_id']) for g in groups for c in g['cases']})==16
plan={'groups':groups,'max_steps':256,'selection':'8 previously unused single-floor Gibson val scenes; first episode in 5-8m and 8-15m strata; if second stratum empty, longest other eligible 5-15m task; endpoint height difference <0.05m; no outcome/score filtering','checkpoint':'public SIGN nav_model.pth plus safety_model.pth','dataset_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'protected':{}}
for tree in ['SIGN-coverage-eval','SIGN-frozen-rollout-coverage','SIGN-frozen-coverage-settle32','SIGN-qwen-topdown-judge']:
 files=subprocess.check_output(['git','-C',str(ROOT/tree),'ls-files','src','exp_config','run_sim.py'],text=True).splitlines()
 plan['protected'][tree]={'head':subprocess.check_output(['git','-C',str(ROOT/tree),'rev-parse','HEAD'],text=True).strip(),'files':{p:hashlib.sha256((ROOT/tree/p).read_bytes()).hexdigest() for p in files}}
(HERE/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(groups,indent=2))
