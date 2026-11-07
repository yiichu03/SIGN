"""Compare finished full-val inputs and metrics; never mix different budgets."""
import json
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
results={};episodes={}
for case in ['coverage256','coverage32']:
    results[case]=json.loads((HERE/case/'result.json').read_text())
    records={}
    for p in (HERE/case/'episodes').glob('*.jsonl'):
        for line in p.read_text().splitlines():
            row=json.loads(line);key=(row['scene_id'],row['episode_id']);assert key not in records;records[key]=row
    assert len(records)==4200
    episodes[case]=records
assert set(episodes['coverage256'])==set(episodes['coverage32'])
for key,a in episodes['coverage256'].items():
    b=episodes['coverage32'][key]
    assert a['goal_sha256']==b['goal_sha256'] and np.allclose(a['start_position'],b['start_position'],rtol=0,atol=1e-6)
summary={'cases':results,'paired_4200_tasks_goals_and_starts_passed':True,
    'training_steps_are_different':True,'note':'Latest individual checkpoints; this is not a matched training-budget comparison.'}
(HERE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
