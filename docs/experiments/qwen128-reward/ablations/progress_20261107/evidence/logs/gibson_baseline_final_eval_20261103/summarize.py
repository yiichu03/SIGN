"""Compare the final frozen baseline with the fixed latest coverage evaluations."""
import hashlib,json
from pathlib import Path
import numpy as np
from guard import guard
HERE=Path(__file__).resolve().parent
COVERAGE=HERE.parent/'gibson_coverage_latest_eval_20261103'
def main():
    guard()
    cases={};episodes={};sources={}
    for case in ['baseline','coverage256','coverage32']:
        folder=(HERE if case=='baseline' else COVERAGE)/case
        result_path=folder/'result.json'
        cases[case]=json.loads(result_path.read_text())
        sources[case]={'result_path':str(result_path),'result_sha256':hashlib.sha256(result_path.read_bytes()).hexdigest()}
        records={}
        for p in (folder/'episodes').glob('*.jsonl'):
            for line in p.read_text().splitlines():
                row=json.loads(line);key=(row['scene_id'],row['episode_id']);assert key not in records;records[key]=row
        expected={tuple(k) for k in json.loads((HERE/'eval_protocol.json').read_text())['episode_keys']}
        assert set(records)==expected and len(records)==4200
        episodes[case]=records
    for case in ['coverage256','coverage32']:
        for key,a in episodes['baseline'].items():
            b=episodes[case][key]
            assert a['goal_sha256']==b['goal_sha256'] and np.allclose(a['start_position'],b['start_position'],rtol=0,atol=1e-6)
    summary={'cases':cases,'source_results':sources,'paired_4200_tasks_goals_and_starts_passed':True,
        'training_steps_are_different':True,'note':'Final frozen baseline 74.240M, coverage256 125.952M, coverage32 48.128M. This is not a matched training-budget comparison.'}
    guard()
    (HERE/'comparison.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
