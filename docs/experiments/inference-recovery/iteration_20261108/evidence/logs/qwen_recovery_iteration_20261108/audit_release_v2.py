"""Read-only release audit for the preregistered neutral-confirmation rule."""
import datetime
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import numpy as np

ROOT=Path('/scratch/e1538633/liuyi')
BASE=ROOT/'logs/qwen_recovery_iteration_20261108/expanded_v2'
COMMIT='f0e093c4d52c595c71f109d69cbf67ae7fbe3daa'
PROTOCOL_SHA='faec250bd4ca4ca9718b137a1f6eac993a86c12024593274484de81ae14cb673'
sys.path.insert(0,str(ROOT/'SIGN-qwen-iter-expanded03/src'))
from recovery_affordance import decision_prefix_audit


def raw_rows(folder):
    result={}
    for path in (folder/'episodes').glob('*.jsonl'):
        for line in path.read_text().splitlines():
            row=json.loads(line);key=(row['scene_id'],row['episode_id'])
            assert key not in result,key
            result[key]=row
    return result


def audit_batch(name,expected):
    batch=BASE/name
    sub=json.loads((batch/'submission.json').read_text())
    assert sub['commit']==COMMIT
    status=json.loads(subprocess.check_output(['qstat','-fx','-F','json',sub['job_id']],text=True))['Jobs']
    status=next(iter(status.values()))
    assert status['job_state']=='F' and status['Exit_status']==0
    result=json.loads((batch/'iteration_result.json').read_text())
    assert result['technical_passed']
    assert set(result['comparisons'])==set(expected)
    summaries={}
    for split,count in expected.items():
        comparison=result['comparisons'][split]
        folders={mode:batch/(split+'_'+mode) for mode in ['off','rule','qwen']}
        rows={mode:raw_rows(folder) for mode,folder in folders.items()}
        for mode,data in rows.items():
            assert len(data)==count and set(data)==set(rows['rule'])
            case=comparison['cases'][mode]
            assert case['source_commit']==COMMIT and case['training_step']==125952000
            assert case['checkpoint_sha256']=='988c9ecc5b0c704e9a4780f636739aec17cbd323d613f0fbdde4699296886c2c'
            assert abs(statistics.mean(r['success'] for r in data.values())-case['success_rate'])<1e-12
            assert abs(statistics.mean(r['spl'] for r in data.values())-case['spl'])<1e-12
            for key,row in data.items():
                assert row['goal_sha256']==rows['rule'][key]['goal_sha256']
                assert row['start_position']==rows['rule'][key]['start_position']
        events_path=folders['qwen']/'native/recovery/events.jsonl'
        events=[json.loads(line) for line in events_path.read_text().splitlines()] if events_path.exists() else []
        rescued=[k for k,r in rows['qwen'].items() if r['success'] and not rows['rule'][k]['success']]
        harmed=[k for k,r in rows['rule'].items() if r['success'] and not rows['qwen'][k]['success']]
        supported=0
        for key in rescued:
            changed=[e for e in events if tuple(e['episode'])==key and e['model'].get('differs_from_rule')]
            if not changed:
                continue
            filename=Path(key[0]).stem+'_'+key[1]+'.npz'
            with np.load(folders['rule']/'audit_traces'/filename,allow_pickle=False) as ref, np.load(folders['qwen']/'audit_traces'/filename,allow_pickle=False) as alt:
                _,prefix=decision_prefix_audit(ref['commands'],ref['poses'],alt['commands'],alt['poses'],[e['decision_step'] for e in changed])
            supported+=int(prefix)
        net=len(rescued)-len(harmed)
        assert net==comparison['net_successes'] and supported==comparison['supported_rescues']
        summaries[split]=dict(episodes=count,net_successes=net,supported_rescues=supported,
            rescues=len(rescued),harms=len(harmed),sr_delta_pp=comparison['sr_delta_pp'],
            spl_delta_pp=comparison['spl_delta_pp'])
    return dict(job_id=sub['job_id'],commit=COMMIT,splits=summaries,
        legacy_passes_fixed_gain_gate=result['passes_fixed_gain_gate'])


def main():
    protocol=BASE/'release_protocol_revision2.json'
    assert hashlib.sha256(protocol.read_bytes()).hexdigest()==PROTOCOL_SHA
    registration=json.loads(protocol.read_text())
    audits={}
    for name,expected in [('expanded03',dict(develop=61,safety=28)),
            ('expanded03_repeat',dict(develop=61,safety=28)),
            ('expanded03_confirmation',dict(confirm=24,general=112,safety=28))]:
        audits[name]=audit_batch(name,expected)
    for name in ['expanded03','expanded03_repeat']:
        current=audits[name]['splits']
        assert current['develop']['net_successes']>=1
        assert current['develop']['supported_rescues']>=1
        assert current['safety']['net_successes']>=0
        assert audits[name]['legacy_passes_fixed_gain_gate']
    confirmation=audits['expanded03_confirmation']['splits']
    for item in confirmation.values():assert item['net_successes']>=0,item
    if confirmation['confirm']['net_successes']>0:
        assert confirmation['confirm']['supported_rescues']>=1
    audit=dict(recorded_at=datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
        release_allowed=True,protocol_sha256=PROTOCOL_SHA,
        protocol_registered_at=registration['registered_at'],behavior_commit=COMMIT,
        audits=audits,old_results_and_dispatch_unchanged=True,
        confirmation_positive_causal_signal=confirmation['confirm']['net_successes']>0,
        interpretation='A neutral confirmation is inconclusive. This audit authorizes only the preplanned formal experiment; it does not establish whole-val benefit. Development is reused and selection-biased.')
    out=BASE/'expanded03_confirmation/version2_release_audit.json'
    assert not out.exists(),'Keep the original release audit'
    out.write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps(audit,indent=2))


if __name__=='__main__':main()
