from pathlib import Path
import ast,json,hashlib,subprocess
ROOT=Path('/scratch/e1538633/liuyi');HERE=Path(__file__).resolve().parent
plan=json.loads((HERE/'plan.json').read_text())
for tree,r in plan['protected'].items():
 assert subprocess.check_output(['git','-C',str(ROOT/tree),'rev-parse','HEAD'],text=True).strip()==r['head']
 for file,h in r['files'].items():assert hashlib.sha256((ROOT/tree/file).read_bytes()).hexdigest()==h,(tree,file)
for group in plan['groups']:
 for case in group['cases']:
  assert (ROOT/'SIGN/data/scene_datasets/gibson'/(case['scene']+'.glb')).is_file()
  assert (ROOT/'SIGN/data/scene_datasets/gibson'/(case['scene']+'.navmesh')).is_file()
for p in HERE.glob('*.py'):ast.parse(p.read_text())
print('Protected sources and 16 task assets verified')
