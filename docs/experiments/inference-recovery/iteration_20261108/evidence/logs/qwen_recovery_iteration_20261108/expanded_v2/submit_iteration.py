"""Freeze one committed source tree and submit one auditable campaign stage."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
ROOT=Path('/scratch/e1538633/liuyi')
HERE=Path(__file__).resolve().parent
DEV=ROOT/'SIGN-qwen-candidate-recovery'


def command(args):
    return subprocess.check_output(args,text=True).strip()


def main():
    p=argparse.ArgumentParser();p.add_argument('--round',required=True);p.add_argument('--stage',choices=['development','confirmation','full'],required=True)
    p.add_argument('--commit',required=True);p.add_argument('--profile',required=True)
    a=p.parse_args();name=a.round if a.stage=='development' else a.round+'_'+a.stage
    if len(a.commit)!=40 or any(c not in '0123456789abcdef' for c in a.commit):
        p.error('Pass the complete immutable commit SHA after awaiting commit completion')
    commit=command(['git','-C',str(DEV),'rev-parse',a.commit])
    command(['git','-C',str(DEV),'cat-file','-e',commit+':'+a.profile])
    b=HERE/name;b.mkdir(exist_ok=True);assert not (b/'submission.json').exists(),'Already submitted'
    tree=ROOT/('SIGN-qwen-iter-'+a.round)
    if not tree.exists():
        subprocess.run(['git','-C',str(DEV),'worktree','add','--detach','--no-checkout',str(tree),commit],check=True)
        subprocess.run(['git','-C',str(tree),'sparse-checkout','set','--cone','src','scripts','tests','exp_config','ckpt','docs/experiments/inference-recovery'],check=True)
        subprocess.run(['git','-C',str(tree),'read-tree','-mu','HEAD'],check=True)
        (tree/'data').symlink_to(ROOT/'SIGN/data')
    assert command(['git','-C',str(tree),'rev-parse','HEAD'])==commit
    assert (tree/a.profile).is_file(),'Profile missing from immutable snapshot'
    tasks=json.loads((HERE/'tasks.json').read_text());tasks['recovery_profile']=a.profile
    (b/'tasks.json').write_text(json.dumps(tasks,indent=2)+'\n')
    old=ROOT/'logs/sign_inference_coverage256_20261108/qwen_active/dev_scan/native/recovery/events.jsonl'
    (b/'probe_inputs.json').write_text(json.dumps(dict(events=str(old),source='old development views, not confirmation'),indent=2)+'\n')
    sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    paths=command(['git','-C',str(tree),'ls-files','src','scripts','tests','exp_config','run_sim.py']).splitlines()
    files={path:sha(tree/path) for path in paths}
    ref=Path(tasks['reference']['directory'])
    assets=[b/'tasks.json',b/'probe_inputs.json',HERE/'selection.json',Path(tasks['checkpoint']['path']),
        ref/'checkpoint.json',ref/'result.json',tree/'ckpt/safety_model.pth',tree/'docs/experiments/inference-recovery/ITERATION_PLAN.md',
        ROOT/'models/Qwen3.5-2B/config.json',ROOT/'models/Qwen3.5-2B/tokenizer.json',
        ROOT/'logs/sign_failure_replay_20261104/analysis/failed_episodes.csv',old]
    assets+=list((ref/'episodes').glob('*.jsonl'))+[Path(x['path']) for x in tasks['splits'].values()]
    for event in map(json.loads,old.read_text().splitlines()):
        assets.extend(Path(x['path']) for x in event['view_files'].values())
    parent=json.loads((ROOT/'logs/sign_inference_coverage256_20261108/rule_full/source_manifest.json').read_text())
    protected=dict(parent['protected_trees']);protected['SIGN-inference-coverage256']=dict(commit=parent['commit'],files=parent['files'])
    (b/'source_manifest.json').write_text(json.dumps(dict(commit=commit,files=files,assets={str(x):sha(x) for x in assets},protected_trees=protected),indent=2)+'\n')
    walltime='06:00:00' if a.stage=='full' else '02:00:00'
    submit=['qsub','-q','autox','-P','CFP04-SF-109','-N','qwen-'+a.round+'-'+a.stage[:3],'-l','walltime='+walltime,
        '-v','ITERATION_TREE='+str(tree)+',ITERATION_BATCH='+str(b)+',ITERATION_STAGE='+a.stage,
        '-o',str(b/'evaluate.pbs.log'),str(tree/'scripts/recovery_iteration.pbs')]
    result=subprocess.run(submit,text=True,capture_output=True)
    record=dict(recorded_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='seconds'),
        command=submit,returncode=result.returncode,stdout=result.stdout,stderr=result.stderr,commit=commit,tree=str(tree),
        stage=a.stage,profile=a.profile,checkpoint=tasks['checkpoint'],source_files=len(files),asset_files=len(set(assets)),
        walltime=walltime,resource='1A40/36CPU/240GB',development_directory_may_advance=True,runtime_snapshot_immutable=True)
    if result.returncode==0:record['job_id']=result.stdout.strip()
    (b/'submission.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2));result.check_returncode()


if __name__=='__main__':main()
