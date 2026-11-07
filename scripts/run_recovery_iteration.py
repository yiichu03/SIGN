#!/usr/bin/env python3
"""Versioned development or untouched confirmation against matched rules."""
import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
TREE=Path(__file__).resolve().parents[1]
from run_active_recovery import run
from evaluate_recovery import guard,read_rows
from src.recovery_affordance import decision_prefix_audit


def compare(batch,split,folders):
    results={m:json.loads((p/'result.json').read_text()) for m,p in folders.items()}
    rows={m:read_rows(p/'episodes') for m,p in folders.items()};reference=rows['rule'];matched=rows['qwen']
    assert set(reference)==set(matched)
    for mode,data in rows.items():
        assert set(data)==set(reference)
        for key,row in data.items():assert row['goal_sha256']==reference[key]['goal_sha256'] and row['start_position']==reference[key]['start_position']
    events_path=folders['qwen']/'native/recovery/events.jsonl'
    events=[json.loads(l) for l in events_path.read_text().splitlines()] if events_path.exists() else []
    rescues=[];harms=[];paired=[]
    for key,row in matched.items():
        changed=[e for e in events if tuple(e['episode'])==key and e['model'].get('differs_from_rule',False)]
        prefix=False;first_difference=None
        if changed:
            scene=Path(key[0]).stem;name=scene+'_'+key[1]+'.npz'
            with np.load(folders['rule']/'audit_traces'/name,allow_pickle=False) as base,np.load(folders['qwen']/'audit_traces'/name,allow_pickle=False) as candidate:
                first_difference,prefix=decision_prefix_audit(base['commands'],base['poses'],
                    candidate['commands'],candidate['poses'],[e['decision_step'] for e in changed])
        rescue=bool(row['success'] and not reference[key]['success']);harm=bool(reference[key]['success'] and not row['success'])
        entry=dict(scene_id=key[0],episode_id=key[1],rule_success=reference[key]['success'],qwen_success=row['success'],
            rule_spl=reference[key]['spl'],qwen_spl=row['spl'],vlm_disagreements=len(changed),
            first_action_difference=first_difference,prefix_until_vlm_decision_matches=prefix,
            human_cause='',human_notes='')
        paired.append(entry)
        if rescue:rescues.append(entry)
        if harm:harms.append(entry)
    with (batch/(split+'_paired.csv')).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(paired[0]));w.writeheader();w.writerows(paired)
    summary=dict(split=split,cases=results,episodes=len(reference),rescues=rescues,harms=harms,
        net_successes=len(rescues)-len(harms),supported_rescues=sum(x['prefix_until_vlm_decision_matches'] for x in rescues),
        sr_delta_pp=100*(results['qwen']['success_rate']-results['rule']['success_rate']),
        spl_delta_pp=100*(results['qwen']['spl']-results['rule']['spl']),
        note='Purpose-selected or separately reserved subset. Prefix audits use simulator telemetry after execution, never as Agent input. Human causes remain blank.')
    extension=json.loads((batch/'tasks.json').read_text()).get('development_extension')
    if split=='develop' and extension:
        selection=json.loads(Path(extension['selection']).read_text())
        groups={'original24':set(map(tuple,selection['original_develop_keys'])),
            'added37':set(map(tuple,selection['added_keys']))}
        assert not (groups['original24'] & groups['added37'])
        assert set.union(*groups.values())==set(reference)
        summary['strata']={}
        for name,keys in groups.items():
            changes=[p for p in paired if (p['scene_id'],p['episode_id']) in keys]
            summary['strata'][name]=dict(episodes=len(keys),
                cases={m:dict(success_rate=float(np.mean([r[k]['success'] for k in keys])),
                    spl=float(np.mean([r[k]['spl'] for k in keys]))) for m,r in rows.items()},
                net_successes=sum(int(p['qwen_success'])-int(p['rule_success']) for p in changes),
                supported_rescues=sum(p['qwen_success']>p['rule_success'] and
                    p['prefix_until_vlm_decision_matches'] for p in changes))
    (batch/(split+'_comparison.json')).write_text(json.dumps(summary,indent=2)+'\n')
    return summary


def main():
    p=argparse.ArgumentParser();p.add_argument('--batch',type=Path,required=True);p.add_argument('--stage',choices=['development','confirmation','full'],required=True)
    a=p.parse_args();b=a.batch.resolve();guard(b)
    if a.stage=='development':
        with (b/'probe.log').open('x') as f:subprocess.run([sys.executable,str(TREE/'scripts/probe_semantic_recovery.py'),'--batch',str(b)],cwd=TREE,stdout=f,stderr=subprocess.STDOUT,check=True)
        paths=[run(b,name,'smoke',mode,native=native,candidate=True) for name,mode,native in [
            ('smoke_native','off',True),('smoke_off','off',False),('smoke_disabled','disabled',False)]]
        assert read_rows(paths[0]/'episodes')==read_rows(paths[1]/'episodes')==read_rows(paths[2]/'episodes')
    summaries={}
    splits=['develop','safety'] if a.stage=='development' else ['confirm','general','safety'] if a.stage=='confirmation' else ['full']
    for split in splits:
        folders={m:run(b,split+'_'+m,split,m,candidate=True) for m in ['off','rule','qwen']}
        summaries[split]=compare(b,split,folders)
    primary=summaries[splits[0]]
    safety=summaries.get('safety')
    candidate=primary['net_successes']>=1 and primary['supported_rescues']>=1
    if safety:candidate=candidate and safety['net_successes']>=0
    if 'general' in summaries:candidate=candidate and summaries['general']['net_successes']>=0
    result=dict(technical_passed=True,stage=a.stage,comparisons=summaries,
        passes_fixed_gain_gate=candidate,
        note='Passing development is exploratory; confirmation must use a frozen commit and untouched cases. No automatic full submission or performance claim from development alone.')
    guard(b);(b/'iteration_result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(stage=a.stage,passes_fixed_gain_gate=candidate,
        subsets={s:dict(net=v['net_successes'],prefix_supported=v['supported_rescues'],sr_delta=v['sr_delta_pp'],spl_delta=v['spl_delta_pp']) for s,v in summaries.items()}),indent=2))


if __name__=='__main__':main()
