"""Compare two fixed candidate checkpoints and three completed reference evaluations."""
import hashlib,json
from pathlib import Path
import numpy as np
from guard import guard
HERE=Path(__file__).resolve().parent
COVERAGE=HERE.parent/'gibson_coverage_latest_eval_20261103'
def main():
    guard()
    cases={};episodes={};sources={}
    folders={'coverage256_143360000':HERE/'coverage143360000', 'coverage256_150528000':HERE/'coverage150528000', 'coverage256_146944000':HERE.parent/'gibson_coverage256_peak_eval_20261105/coverage256', 'coverage256_previous':COVERAGE/'coverage256', 'baseline':HERE.parent/'gibson_baseline_final_eval_20261103/baseline'}
    for case,folder in folders.items():
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
    for case in folders:
        if case == 'baseline':
            continue
        for key,a in episodes['baseline'].items():
            b=episodes[case][key]
            assert a['goal_sha256']==b['goal_sha256'] and np.allclose(a['start_position'],b['start_position'],rtol=0,atol=1e-6)
    summary={'cases':cases,'source_results':sources,'paired_4200_tasks_goals_and_starts_passed':True,
        'training_steps_are_different':True,'note':'Coverage256 candidates fixed from training curves:143.360M and150.528M. References:coverage256125.952M/146.944M and frozen baseline74.240M. Different training budgets; single-seed checkpoint comparison, not a matched-budget causal reward comparison.'}
    summary['candidate_checkpoints']=json.loads((HERE/'manifest.json').read_text())['cases']
    summary['delta_vs_previous_coverage256_pp']={case:{k:100*(cases[case][k]-cases['coverage256_previous'][k]) for k in ['success_rate','spl']} for case in ['coverage256_143360000','coverage256_150528000']}
    guard()
    (HERE/'comparison.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
