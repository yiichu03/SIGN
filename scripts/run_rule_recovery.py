#!/usr/bin/env python3
"""Check the corrected checkpoint, then compare native policy and rule on all val."""
import argparse
import csv
import json
from pathlib import Path
import statistics
from run_active_recovery import run
from evaluate_recovery import guard, read_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch', type=Path, required=True)
    batch = parser.parse_args().batch.resolve()
    guard(batch)
    smoke = [run(batch, name, 'smoke', mode, native=native, active=False)
        for name, mode, native in [('smoke_native', 'off', True),
            ('smoke_off', 'off', False), ('smoke_disabled', 'disabled', False)]]
    assert read_rows(smoke[0]/'episodes') == read_rows(smoke[1]/'episodes') == read_rows(smoke[2]/'episodes')
    (batch/'technical_gate.json').write_text(json.dumps(dict(passed=True,
        native_off_zero_intervention_exact=True, checkpoint=json.loads((batch/'tasks.json').read_text())['checkpoint']), indent=2)+'\n')
    native = run(batch, 'full_off', 'full', 'off', active=False)
    rule = run(batch, 'full_rule', 'full', 'rule', active=False)
    a, b = read_rows(rule/'episodes'), read_rows(native/'episodes')
    assert set(a) == set(b) and len(a) == 4200
    episodes = {tuple(r['episode']): r for r in map(json.loads,
        (rule/'native/recovery/episodes.jsonl').read_text().splitlines())}
    assert set(episodes) == set(a)
    paired, scenes = [], []
    for key, row in sorted(a.items()):
        assert row['goal_sha256'] == b[key]['goal_sha256'] and row['start_position'] == b[key]['start_position']
        h = episodes[key]
        assert h['actions_sha256'] == row['actual_actions_sha256'] and h['steps'] == row['steps']
        assert h['overrides'] <= 20 and h['survey_steps'] == 0
        outcome = ('failure_to_success' if row['success'] and not b[key]['success'] else
            'success_to_failure' if b[key]['success'] and not row['success'] else 'unchanged')
        paired.append(dict(scene_id=key[0], episode_id=key[1], outcome=outcome,
            off_success=b[key]['success'], success=row['success'], off_spl=b[key]['spl'], spl=row['spl'],
            attempts=h['attempts'], overrides=h['overrides'], human_primary_cause='', human_notes=''))
    for scene in sorted({key[0] for key in a}):
        keys = [key for key in a if key[0] == scene]
        scenes.append(dict(scene_id=scene, episodes=len(keys), off_sr=statistics.mean(b[k]['success'] for k in keys),
            rule_sr=statistics.mean(a[k]['success'] for k in keys), off_spl=statistics.mean(b[k]['spl'] for k in keys),
            rule_spl=statistics.mean(a[k]['spl'] for k in keys)))
    for name, rows in [('paired_tasks', paired), ('per_scene', scenes)]:
        with (batch/(name+'.csv')).open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    results = {name: json.loads((folder/'result.json').read_text()) for name, folder in [('off', native), ('rule', rule)]}
    assert not results['rule']['harness']['worker_started']
    result = dict(passed=True, cases=results, paired_4200_tasks_goals_starts=True,
        sr_delta_pp=100*(results['rule']['success_rate']-results['off']['success_rate']),
        spl_delta_pp=100*(results['rule']['spl']-results['off']['spl']),
        outcome_counts={name: sum(row['outcome'] == name for row in paired)
            for name in ['failure_to_success', 'success_to_failure', 'unchanged']},
        changed_without_direct_intervention=[row for row in paired if row['outcome'] != 'unchanged' and row['overrides'] == 0],
        note='Both arms use the same coverage256125.952M checkpoint. Off is freshly rerun and strictly checked against its cached full native reference. No training or Qwen in this suite; paired changes are not all necessarily causal intervention effects.')
    guard(batch)
    (batch/'comparison.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['cases','changed_without_direct_intervention']}, indent=2))


if __name__ == '__main__':
    main()
