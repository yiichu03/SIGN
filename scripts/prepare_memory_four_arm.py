#!/usr/bin/env python3
"""Prepare immutable manifests/commands only. This script never submits jobs."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
TREE=Path(__file__).resolve().parents[1]
ROOT=TREE.parent

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    commit=subprocess.check_output(['git','-C',str(TREE),'rev-parse','HEAD'],text=True).strip()
    dirty=subprocess.check_output(['git','-C',str(TREE),'diff','HEAD','--','src','scripts','tests','exp_config','run_sim.py'],text=True)
    if dirty:raise RuntimeError('Commit runtime files before preparation')
    parent=ROOT/'logs/qwen_recovery_iteration_20261108/expanded_v2/expanded03_full'
    old=json.loads((parent/'tasks.json').read_text());tasks={k:old[k] for k in ('checkpoint','reference')}
    full=old['splits']['full'];data=json.loads(gzip.decompress(Path(full['path']).read_bytes()))
    # Six scenes chosen by stable task hash, independently of behavior/outcomes.
    ranked=sorted(data['episodes'],key=lambda e:hashlib.sha256((e['scene_id']+':'+str(e['episode_id'])).encode()).hexdigest())
    selected=[];scenes=set()
    for e in ranked:
        if e['scene_id'] not in scenes:selected.append(e);scenes.add(e['scene_id'])
        if len(selected)==6:break
    # Add previously observed trigger episodes only to exercise integration,
    # never to tune parameters or claim SR. Formal tasks remain the full 4200.
    trigger_rows=[json.loads(l) for l in (parent/'full_qwen/native/recovery/events.jsonl').read_text().splitlines()]
    known={tuple(r['episode']) for r in trigger_rows}
    selected_keys={(e['scene_id'],str(e['episode_id'])) for e in selected}
    for e in ranked:
        key=(e['scene_id'],str(e['episode_id']))
        if key in known and key not in selected_keys:selected.append(e);selected_keys.add(key)
        if len(selected)==12:break
    dataset=out/'datasets';dataset.mkdir()
    path=dataset/'smoke.json.gz';path.write_bytes(gzip.compress(json.dumps(dict(data,episodes=selected)).encode(),mtime=0))
    tasks['splits']=dict(full=full,smoke=dict(path=str(path),sha256=sha(path),episodes=len(selected),
        episode_keys=[[e['scene_id'],str(e['episode_id'])] for e in selected]))
    tasks.update(save_audit_traces=True,smoke_selection='six distinct scenes by stable SHA ordering plus six previous trigger episodes for engineering coverage; not a performance subset',
        frozen_settings='PLAN.md; no old61 tuning',formal_jobs_submitted=False)
    write(out/'tasks.json',tasks)
    probes=[]
    for r in map(json.loads,(parent/'full_qwen/native/recovery/events.jsonl').read_text().splitlines()):
        if r.get('view_files'):
            probes.append(dict(id=r['id'],episode=r['episode'],view_files=r['view_files'],view_steps=r['view_steps']))
        if len(probes)==2:break
    write(out/'probe_inputs.json',probes)
    names=subprocess.check_output(['git','-C',str(TREE),'ls-files','src','scripts','tests','exp_config','run_sim.py'],text=True).splitlines()
    assets=[out/'tasks.json',out/'probe_inputs.json',TREE/'ckpt/safety_model.pth',Path(tasks['checkpoint']['path']),
        ROOT/'models/Qwen3.5-2B/config.json',ROOT/'models/Qwen3.5-2B/tokenizer.json']
    ref=Path(tasks['reference']['directory']);assets += [ref/'checkpoint.json',ref/'result.json']+list((ref/'episodes').glob('*.jsonl'))
    assets += [Path(x['path']) for x in tasks['splits'].values()]
    assets += [Path(v['path']) for r in probes for v in r['view_files'].values()]
    protected=json.loads((parent/'source_manifest.json').read_text()).get('protected_trees',{})
    write(out/'source_manifest.json',dict(commit=commit,files={n:sha(TREE/n) for n in names},
        assets={str(x):sha(x) for x in assets},protected_trees=protected))
    commands={}
    from memory_four_arm import ARMS
    for arm in ARMS:
        if arm=='disabled':continue
        cmd=['qsub','-q','autox','-P','CFP04-SF-109','-N','memory-'+arm,'-v',
            'MEMORY_TREE='+str(TREE)+',MEMORY_BATCH='+str(out)+',MEMORY_ARM='+arm,
            '-o',str(out/('pbs_'+arm+'.log')),str(TREE/'scripts/memory_four_arm.pbs')]
        commands[arm]=shlex.join(cmd)
    write(out/'prepared_commands.json',dict(commit=commit,submitted=False,commands=commands))
    (out/'formal_commands.sh').write_text('# Commands for user review only. Not executed by the preparer.\n'+'\n'.join(commands.values())+'\n')
    print(json.dumps(dict(output=str(out),commit=commit,submitted=False,smoke_tasks=tasks['splits']['smoke']['episode_keys']),indent=2))

if __name__=='__main__':main()
