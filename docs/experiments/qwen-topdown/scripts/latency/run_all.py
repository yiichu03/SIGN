from pathlib import Path
import json,subprocess,sys,time,hashlib,os
ROOT=Path('/scratch/e1538633/liuyi');HERE=Path(__file__).resolve().parent;TREE=ROOT/'SIGN-qwen-topdown-judge'
plan=json.loads((HERE/'plan.json').read_text())
for rel,h in plan['source_hashes'].items():assert hashlib.sha256((TREE/rel).read_bytes()).hexdigest()==h,rel
assert os.environ.get('PBS_JOBID')
status={'job':os.environ['PBS_JOBID'],'status':'running','models':{}}
for size in plan['models']:
 name='Qwen3.5-'+size;model=ROOT/'models'/name
 if size!='9B':assert (HERE/('download_'+size+'.json')).is_file(), 'Download validation incomplete'
 status['current_model']=name;(HERE/'runtime.json').write_text(json.dumps(status,indent=2))
 command=[sys.executable,str(TREE/'scripts/benchmark_qwen_single.py'),'--model-dir',str(model),'--prompt',str(HERE/'prompt.txt'),'--out',str(HERE/name),'--images']+plan['images']
 start=time.time()
 with (HERE/(name+'.log')).open('x') as log:p=subprocess.run(command,cwd=TREE,stdout=log,stderr=subprocess.STDOUT)
 status['models'][name]={'returncode':p.returncode,'process_wall_seconds':time.time()-start}
 print(name,status['models'][name],flush=True)
status['status']='complete' if all(x['returncode']==0 for x in status['models'].values()) else 'failed'
(HERE/'runtime.json').write_text(json.dumps(status,indent=2))
if status['status']!='complete':raise SystemExit(1)
