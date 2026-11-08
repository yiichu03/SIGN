"""Capture branches, worktrees and runtime guards for a documentation-only push."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path('/scratch/e1538633/liuyi')
HERE=Path(__file__).resolve().parent
DEV=ROOT/'SIGN-qwen-candidate-recovery'
SSH='ssh -o IdentityAgent=none -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=20 -i /home/svu/e1538633/.ssh/id_ed25519'


def git(tree,*args):
    return subprocess.check_output(['git','-C',str(tree),*args],text=True,
        env=dict(os.environ,GIT_SSH_COMMAND=SSH)).strip()


def trees(tree):
    result=[]
    for block in git(tree,'worktree','list','--porcelain').split('\n\n'):
        values=dict(line.split(' ',1) for line in block.splitlines() if ' ' in line)
        result.append(dict(path=values['worktree'],commit=values['HEAD'],
            branch=values.get('branch','').removeprefix('refs/heads/') or None))
    return result


def capture_repository(name,tree):
    remote={ref.removeprefix('refs/heads/'):sha for sha,ref in
        (line.split() for line in git(tree,'ls-remote','--heads','origin').splitlines())}
    worktrees=trees(tree);branches=[]
    for line in git(tree,'for-each-ref','--format=%(refname:short)|%(objectname)|%(upstream:short)','refs/heads').splitlines():
        branch,local,tracking=line.split('|')
        row=dict(name=branch,local_commit=local,origin_commit=remote.get(branch),tracking=tracking or None,
            worktrees=[x['path'] for x in worktrees if x['branch']==branch])
        if remote.get(branch)==local:
            row['relationship']='same_commit'
        elif branch not in remote:
            row['relationship']='local_only'
        else:
            known=subprocess.run(['git','-C',str(tree),'cat-file','-e',remote[branch]+'^{commit}'],capture_output=True).returncode==0
            if known:
                row['ahead_behind']=git(tree,'rev-list','--left-right','--count',local+'...'+remote[branch]).split()
                row['runtime_diff_files']=git(tree,'diff','--name-only',local,remote[branch],'--','src','scripts','tests','exp_config','run_sim.py').splitlines()
                row['relationship']='different_commit_same_runtime' if not row['runtime_diff_files'] else 'runtime_differs'
            else:
                row['relationship']='different_remote_object_not_fetched'
        branches.append(row)
    return dict(repository='yiichu03/'+name,tree=str(tree),
        fetch_url=git(tree,'remote','get-url','origin'),push_url=git(tree,'remote','get-url','--push','origin'),
        branches=branches,origin_heads=remote,remote_only_names=sorted(set(remote)-{x['name'] for x in branches}),
        worktrees=worktrees,named_branch_count=len(branches),origin_branch_count=len(remote),
        detached_worktree_count=sum(x['branch'] is None for x in worktrees))


def capture_guards(repositories):
    guards={}
    for repo in repositories.values():
        for item in repo['worktrees']:
            tree=Path(item['path'])
            paths=git(tree,'ls-files','src','scripts','tests','exp_config','run_sim.py').splitlines()
            files={p:hashlib.sha256((tree/p).read_bytes()).hexdigest() for p in paths}
            guards[str(tree)]=dict(commit=item['commit'],files=files)
    return guards


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check-guards',action='store_true');args=parser.parse_args()
    if args.check_guards:
        guards=json.loads((HERE/'protected_trees.json').read_text())
        for path,item in guards.items():
            tree=Path(path)
            if tree!=DEV:
                assert git(tree,'rev-parse','HEAD')==item['commit'],path
            for p,sha in item['files'].items():
                assert hashlib.sha256((tree/p).read_bytes()).hexdigest()==sha,(path,p)
        print('Unchanged runtime files in',len(guards),'worktrees; only documentation branch HEAD may advance.')
        return
    assert not (HERE/'branch_inventory.json').exists(),'Preserve the captured branch snapshot'
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda x:capture_repository(*x),[('SIGN',DEV),('SIGN-SRU',ROOT/'SIGN-SRU')]))
    repositories={x['repository'].split('/')[-1]:x for x in results}
    inventory=dict(captured_at=datetime.now().astimezone().isoformat(timespec='seconds'),
        repositories=repositories,scope='Local and origin named branches; publication branch HEAD is recorded before this docs commit. Detached worktrees are not named branches.')
    (HERE/'branch_inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    (HERE/'protected_trees.json').write_text(json.dumps(capture_guards(repositories),indent=2)+'\n')
    for name,r in repositories.items():
        print(name,'local',r['named_branch_count'],'origin',r['origin_branch_count'],
            'worktrees',len(r['worktrees']),'detached',r['detached_worktree_count'])
        for b in r['branches']:
            if b['relationship']!='same_commit':print(b['name'],b['relationship'],b.get('runtime_diff_files'))


if __name__=='__main__':main()
