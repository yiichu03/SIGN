"""Compare three selected Qwen-trained models and completed reference evaluations."""
import hashlib,json
from pathlib import Path
import numpy as np
from guard import guard
HERE=Path(__file__).resolve().parent
COVERAGE=HERE.parent/'gibson_coverage_latest_eval_20261103'
def main():
    guard()
    cases={};episodes={};sources={}
    folders={'qwen01':HERE/'qwen01', 'A':HERE/'A', 'B':HERE/'B', 'baseline':HERE.parent/'gibson_baseline_final_eval_20261103/baseline', 'coverage256_125952000':COVERAGE/'coverage256', 'coverage32_48128000':COVERAGE/'coverage32', 'coverage256_146944000':HERE.parent/'gibson_coverage256_peak_eval_20261105/coverage256'}
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
        'training_steps_are_different':True,'note':'Qwen-trained checkpoints selected using frozen training curves only:beta0.1 20.480M, A36.352M, B29.696M. Native navigation evaluation has no Qwen worker or Qwen trajectory collection. Different training budgets; reference scores are not matched-budget causal controls.'}
    summary['candidate_checkpoints']=json.loads((HERE/'manifest.json').read_text())['cases']
    summary['delta_vs_reference_pp']={case:{ref:{k:100*(cases[case][k]-cases[ref][k]) for k in ['success_rate','spl']} for ref in ['baseline','coverage256_125952000','coverage32_48128000','coverage256_146944000']} for case in ['qwen01','A','B']}
    guard()
    (HERE/'comparison.json').write_text(json.dumps(summary,indent=2)+'\n')
    import csv
    with (HERE/'comparison.csv').open('w') as f:
        writer=csv.writer(f)
        writer.writerow(['case','training_step','episodes','sr','spl','mean_collisions','mean_episode_steps','new_m2_per_step_global'])
        for case,r in cases.items():
            writer.writerow([case,r['training_step'],r['episodes'],r['success_rate'],r['spl'],r['mean_collisions'],r['mean_episode_steps'],r['new_m2_per_step_global']])
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
