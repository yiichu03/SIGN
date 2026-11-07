"""Freeze reused development inputs and a disjoint confirmation subset."""
import csv,gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'logs/sign_inference_active_view_20261108'

def main():
 HERE.mkdir(exist_ok=True);assert not (HERE/'tasks.json').exists()
 old=json.loads((ROOT/'logs/sign_inference_harness_20261107/tasks.json').read_text())
 raw=Path(old['splits']['full']['path']);allrows=json.loads(gzip.decompress(raw.read_bytes()))['episodes']
 key=lambda x:(x['scene_id'],str(x['episode_id']))
 index={key(r):r for r in allrows};oldsmoke={tuple(k) for k in old['splits']['smoke']['episode_keys']};oldpilot={tuple(k) for k in old['splits']['pilot']['episode_keys']}
 events=[json.loads(l) for l in (ROOT/'logs/sign_inference_harness_20261107/retry2/pilot/pilot_qwen/native/recovery/events.jsonl').read_text().splitlines()]
 devkeys=oldsmoke|{tuple(e['episode']) for e in events}
 review={(r['scene_id'],r['episode_id']) for r in csv.DictReader((ROOT/'logs/sign_failure_replay_20261104/analysis/review/human_review.csv').open())}
 excluded=oldsmoke|oldpilot|review|devkeys
 development=[index[k] for k in sorted(devkeys)]
 confirm=[]
 for scene in sorted({k[0] for k in index}):
  eligible=[r for k,r in index.items() if k[0]==scene and k not in excluded]
  eligible.sort(key=lambda r:hashlib.sha256(('|'.join(key(r))+'|active-confirm-v2').encode()).hexdigest())
  assert len(eligible)>=20;confirm.extend(eligible[:20])
 assert len(confirm)==280 and not {key(x) for x in confirm}&excluded
 splits={}
 for name,rows in [('smoke',development),('pilot',confirm)]:
  path=HERE/'datasets'/name/'val.json.gz';path.parent.mkdir(parents=True)
  path.write_bytes(gzip.compress(json.dumps({'episodes':rows},separators=(',',':')).encode(),mtime=0))
  splits[name]=dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),episode_keys=[list(key(r)) for r in rows],episodes=len(rows))
 splits['full']=old['splits']['full']
 result=dict(splits=splits,checkpoint=old['checkpoint'],development_reuses_previous_cases=True,
  confirmation_excludes_all_old_pilot_and_smoke_and_review=True,old_pilot_keys=[list(k) for k in sorted(oldpilot)],
  note='Fixed development/confirmation separation inside reused Gibson val; no independent unseen benchmark claim.')
 (HERE/'tasks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v['episodes'] for k,v in splits.items()}))
if __name__=='__main__':main()
