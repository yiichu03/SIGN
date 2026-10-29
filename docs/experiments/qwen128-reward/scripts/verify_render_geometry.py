"""Replay all published trajectories incrementally and check both real windows."""
import gzip,json,sys
from pathlib import Path
import numpy as np
ROOT=Path('/scratch/e1538633/liuyi');TREE=ROOT/'SIGN-qwen128-reward';sys.path.insert(0,str(TREE))
from src.qwen_geometry import EpisodeCoverage
from habitat.utils.visualizations import fog_of_war
base=TREE/'docs/experiments/qwen-history-solid';manifest=json.loads((base/'windows.json').read_text())
checks=[]
for s in manifest['segments']:
    t=json.loads(gzip.decompress((base/'sources'/s['trajectory_id']/'trajectory.json.gz').read_bytes()))
    with np.load(base/s['masks']) as a:
        g=EpisodeCoverage(a['grid'])
        for i,p in enumerate(t['poses'][:s['end']+1]):
            g.observe(a['coords'][i],p['heading_rad'],p['position_xyz'])
            if i==s['start']:g.cut()
        snap=g.snapshot();assert snap['valid_geometry'],(s['id'],snap['geometry_reason'])
        assert np.array_equal(snap['prior_seen'],a['prior_seen'])
        assert np.array_equal(snap['final_seen'],a['final_seen'])
        assert snap['metadata']==s['history_stats']
        checks.append(dict(id=s['id'],actions=s['action_count'],history=s['start'],masks_and_stats_exact=True))
# A solid wall blocks visibility. Compare same-map unblocked geometry at the same heading.
grid=np.ones((120,120),dtype=np.uint8);grid[:,70]=0
blocked=EpisodeCoverage(grid,mpp=.025);blocked.observe((60,50),np.pi/2,[0,0,0])
open_map=EpisodeCoverage(np.ones_like(grid),mpp=.025);open_map.observe((60,50),np.pi/2,[0,0,0])
# This heading looks toward increasing columns in Habitat's map convention.
assert open_map.seen[:,75:].sum()>0
assert blocked.seen[:,75:].sum()==0
report=dict(passed=True,published_windows=len(checks),published_trajectories=len({s['trajectory_id'] for s in manifest['segments']}),
            all_masks_statistics_exact=True,solid_wall_occlusion_verified=True,checks=checks)
(ROOT/'logs/qwen128_reward_20261029/offline_online_geometry.json').write_text(json.dumps(report,indent=2)+'\n')
print('Exact',len(checks),'windows; wall occlusion passed')
