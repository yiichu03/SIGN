"""Eight independent environments across rollouts with random real resets."""
import copy,json,sys
from pathlib import Path
import numpy as np
import torch
ROOT=Path('/scratch/e1538633/liuyi');sys.path.insert(0,str(ROOT/'SIGN-qwen128-reward'))
from src.qwen_rollout import SegmentCollector,SegmentLedger,PAYLOAD_KEY
rng=np.random.default_rng(100);N,H=8,256;ledger=SegmentLedger(N,H)
cs=[SegmentCollector() for _ in range(N)]
for env,c in enumerate(cs):c.env_id=env;c.reset('scene',str(env)+'_0',None,'fixture')
all_ids=set();segments=0
for rollout in range(6):
    masks=torch.ones(H+1,N,1,dtype=torch.bool);nav=torch.as_tensor(rng.normal(size=(H+1,N,1)));rewards=nav.clone();nav_before=nav.clone();mb=masks.clone()
    for row in range(H):
        dones=(rng.random(N)<.027).tolist()
        # Explicit terminal/128/rollout collisions and multiple episodes within one block.
        if row in [0,126,127,128,254,255]:dones[row%N]=True
        infos=[]
        for env,c in enumerate(cs):
            payload=c.step((0,0),0.,[0.,0.,0.],dones[env])
            for snap in payload[1]:snap['valid_geometry']=rng.random()>.1
            infos.append({PAYLOAD_KEY:copy.deepcopy(payload),'navigation':1.})
            masks[row+1,env,0]=not dones[env]
            if dones[env]:c.reset('scene',str(env)+'_'+str(c.reset_index+1),None,'fixture')
        ledger.collect(row,dones,infos)
        assert all(PAYLOAD_KEY not in info for info in infos)
    mb=masks.clone();valid=[s for s in ledger.pending if s['valid_geometry']]
    responses=[dict(id=s['segment_id'],valid=True,q=float(rng.random())) for s in valid]
    bonuses=ledger.add(rewards,masks,responses,.1)
    assert len({s['segment_id'] for s in ledger.pending})==len(ledger.pending)
    assert not all_ids.intersection(s['segment_id'] for s in ledger.pending)
    all_ids.update(s['segment_id'] for s in ledger.pending);segments+=len(ledger.pending)
    expected=torch.zeros_like(rewards)
    for s,r in zip(valid,responses):expected[s['end_row'],s['env_id'],0]+=.1*s['action_count']/H*r['q']
    torch.testing.assert_close(rewards-nav,expected,atol=5e-16,rtol=0)
    assert masks.equal(mb) and nav.equal(nav_before)
    ledger.advance()
report=dict(passed=True,environments=N,rollouts=6,transitions=N*H*6,segments=segments,
    exact_end_rows=True,no_duplicate_ids=True,masks_unchanged=True,navigation_rewards_unchanged=True)
(ROOT/'logs/qwen128_reward_20261029/addressing_validation.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
