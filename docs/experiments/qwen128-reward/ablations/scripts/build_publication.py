"""Extend existing Qwen experiment evidence in a detached tree; no live source edits."""
import argparse,hashlib,json,os,re,shutil,subprocess
from pathlib import Path
ROOT=Path('/scratch/e1538633/liuyi');HERE=Path(__file__).resolve().parent;TRAIN=ROOT/'SIGN-qwen-ablation'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--tree',type=Path,required=True);a=p.parse_args();tree=a.tree
    package=tree/'docs/experiments/qwen128-reward';folder=package/'ablations'
    for name,record in json.loads((package/'publication_manifest.json').read_text()).items():assert sha(package/name)==record['sha256'],name
    old=(package/'workspace/WORKLOG.md').read_bytes();assert (ROOT/'WORKLOG.md').read_bytes().startswith(old)
    for name in ['scripts','evidence']:(folder/name).mkdir(exist_ok=False)
    for f in HERE.iterdir():
        if f.suffix in ('.py','.pbs'):
            shutil.copyfile(f,folder/'scripts'/f.name)
    for name in ['source_manifest.json','config_audit.json','resource_preflight.json','short_submission.json','formal_submission.json','first_input_parity.json','control_input_parity.json','waiter_validation.json','milestone_validation.json','first_formal_events.json','unit_tests_pass.log']:
        shutil.copyfile(HERE/name,folder/'evidence'/name)
    shutil.copyfile(HERE/'eval_protocol.json',folder/'evidence/eval_protocol.json')
    for case in ['A','B','C']:
        dest=folder/'evidence'/case;dest.mkdir()
        for name in ['short_validation.json','short_scalars.csv','short_command.json','formal_command.json','formal_config_preinit.yaml','formal_effective_config.yaml']:
            if (HERE/case/name).exists():shutil.copyfile(HERE/case/name,dest/name)
        source=TRAIN/'results/qwen_ablation_20261029'/case/'short_40960/qwen'
        for name in ['segments.jsonl','rollouts.jsonl','effective_config.yaml','initial_parameter_hashes.json','worker_boot.json','verification.json']:
            if (source/name).exists():shutil.copyfile(source/name,dest/name)
    (folder/'README.md').write_text((HERE/'report.md').read_text())
    readme=package/'README.md';s=readme.read_text();s+='\n\n## A/B/C beta0.03与匹配几何128对照\n\n基于33e30d2的独立实验、冻结校准及实际作业见 [A/B/C实验记录](ablations/README.md)。原beta0.1正式训练1507268及旧coverage和评估依赖继续保留。\n';readme.write_text(s)
    for name in ['AGENTS.md','STATUS.md','RUNBOOK.md','WORKLOG.md']:
        current=(ROOT/name).read_bytes()
        if name=='WORKLOG.md':(package/'workspace'/name).write_bytes(current);continue
        def portable(m):
            label,target=m.groups()
            if target.startswith(('http://','https://','#')) or target.split('#')[0] in ['AGENTS.md','STATUS.md','RUNBOOK.md','WORKLOG.md']:return m.group(0)
            path=ROOT/target.split('#')[0]
            if str(path).startswith(str(TRAIN)+'/'):
                mapped=tree/path.relative_to(TRAIN)
                if mapped.exists():return '['+label+']('+os.path.relpath(mapped,package/'workspace')+')'
            return label+'（服务器路径：`'+str(path)+'`）'
        (package/'workspace'/name).write_text(re.sub(r'\[([^\]]+)\]\(([^)]+)\)',portable,current.decode()))
    manifest={str(f.relative_to(package)):dict(sha256=sha(f),bytes=f.stat().st_size) for f in sorted(package.rglob('*')) if f.is_file() and f.name!='publication_manifest.json'}
    (package/'publication_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    for f,record in manifest.items():assert sha(package/f)==record['sha256']
    assert not subprocess.check_output(['git','diff','d2352f0','--','src','scripts','tests','exp_config','run_sim.py'],cwd=tree,text=True)
    print(json.dumps(dict(files=len(manifest),bytes=sum(r['bytes'] for r in manifest.values())),indent=2))
if __name__=='__main__':main()
