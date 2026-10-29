"""Generate a small evidence package and root-doc snapshots in a detached tree."""
import argparse,hashlib,json,os,re,shutil,subprocess
from pathlib import Path
ROOT=Path('/scratch/e1538633/liuyi');HERE=Path(__file__).resolve().parent
TRAIN=ROOT/'SIGN-qwen128-reward';DOCS='docs/experiments/qwen128-reward'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--tree',type=Path,required=True);p.add_argument('--progress',type=Path);a=p.parse_args();tree=a.tree
    package=tree/DOCS
    if a.progress:
        old=json.loads((package/'publication_manifest.json').read_text())
        for name,record in old.items():assert sha(package/name)==record['sha256'],name
        assert (ROOT/'WORKLOG.md').read_bytes().startswith((package/'workspace/WORKLOG.md').read_bytes())
    package.mkdir(parents=True,exist_ok=bool(a.progress))
    for sub in ['scripts','evidence','samples','workspace']:(package/sub).mkdir(exist_ok=bool(a.progress))
    for f in HERE.iterdir():
        if f.suffix in ('.py','.pbs','.sh'):shutil.copyfile(f,package/'scripts'/f.name)
    for name in ['source_manifest.json','config_audit.json','formal_effective_config.yaml','short_validation.json','submission.json','eval_protocol.json','first_training_events.json','offline_online_geometry.json','eval_watch_state.json','watcher_validation.json','addressing_validation.json','eval_config_validation.json','eval_effective_config.yaml','milestone_validation.json']:
        source=HERE/name
        if source.exists():shutil.copyfile(source,package/'evidence'/name)
    for name in ['qwen128_unittest_full.log']:
        shutil.copyfile(ROOT/'logs'/name,package/'evidence'/name)
    run=TRAIN/'results/qwen128_reward_20261029/short_qwen_40960/qwen'
    for name in ['verification.json','worker_boot.json','prompt.txt','rollouts.jsonl','segments.jsonl','initial_parameter_hashes.json']:
        shutil.copyfile(run/name,package/'evidence'/name)
    sample_files=sorted((run/'samples').glob('*.json'))
    chosen=sorted(sample_files,key=lambda p:json.loads(p.read_text())['identity']['start'],reverse=True)[:2]
    for f in chosen:
        for suffix in ['.json','.png','.npz']:shutil.copyfile(f.with_suffix(suffix),package/'samples'/f.with_suffix(suffix).name)
        # Keep original request path as audit, add a working portable preview reference.
        dest=package/'samples'/f.name;data=json.loads(dest.read_text())
        data['original_input_image']=data['row']['image'];data['sample_image']=f.with_suffix('.png').name
        dest.write_text(json.dumps(data,indent=2)+'\n')
    if a.progress:
        destination=package/'evidence'/a.progress.name
        shutil.copytree(a.progress,destination)
    for name in ['AGENTS.md','STATUS.md','RUNBOOK.md','WORKLOG.md']:
        current=(ROOT/name).read_bytes()
        prior=tree/'docs/experiments/qwen-history-solid/workspace'/name
        if name=='WORKLOG.md' and prior.exists():assert current.startswith(prior.read_bytes()),'Published WORKLOG prefix changed'
        if name=='WORKLOG.md':
            (package/'workspace'/name).write_bytes(current)
        else:
            # Generated snapshots keep links to the four local docs. External server
            # artifacts are explicitly shown as server paths instead of broken GitHub links.
            def portable(match):
                label,target=match.groups()
                if target.startswith(('http://','https://','#')) or target.split('#')[0] in ['AGENTS.md','STATUS.md','RUNBOOK.md','WORKLOG.md']:
                    return match.group(0)
                path=ROOT/target.split('#')[0]
                if str(path).startswith(str(TRAIN)+'/'):
                    mapped=tree/path.relative_to(TRAIN)
                    if mapped.exists():
                        link=os.path.relpath(mapped,package/'workspace')
                        if '#' in target:link+='#'+target.split('#',1)[1]
                        return '['+label+']('+link+')'
                return label+'（服务器路径：`'+str(path)+'`）'
            content=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',portable,current.decode())
            (package/'workspace'/name).write_text(content)
    (package/'README.md').write_text((HERE/'report.md').read_text())
    manifest={str(f.relative_to(package)):dict(sha256=sha(f),bytes=f.stat().st_size) for f in sorted(package.rglob('*')) if f.is_file() and f.name!='publication_manifest.json'}
    (package/'publication_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    for file,record in manifest.items():assert sha(package/file)==record['sha256']
    # No source/config changes relative to the frozen runtime commit.
    diff=subprocess.check_output(['git','diff','HEAD','--','src','scripts','tests','exp_config','run_sim.py'],cwd=tree,text=True)
    assert not diff
    readme=tree/'README.md';s=readme.read_text();line='Qwen128 training reward and verified short-run evidence: [experiment record](docs/experiments/qwen128-reward/README.md).'
    if line not in s:s+='\n\n'+line+'\n'
    readme.write_text(s)
    print(json.dumps(dict(files=len(manifest),bytes=sum(x['bytes'] for x in manifest.values())),indent=2))
if __name__=='__main__':main()
