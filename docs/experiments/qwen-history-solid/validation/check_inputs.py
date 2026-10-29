from pathlib import Path
import json,hashlib,subprocess,sys,os
root=Path('/scratch/e1538633/liuyi');here=Path(__file__).resolve().parent
m=json.loads((here/'input_guard.json').read_text())
for name,r in m['protected'].items():
 tree=root/name
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=tree,text=True).strip()==r['head'],name
 for file,h in r['files'].items():assert hashlib.sha256((tree/file).read_bytes()).hexdigest()==h,(name,file)
source=Path(m['source_package']);published=json.loads((source/'publication_manifest.json').read_text())
assert hashlib.sha256((source/'publication_manifest.json').read_bytes()).hexdigest()==m['source_publication_manifest_sha256']
for file,r in published['files'].items():assert hashlib.sha256((source/file).read_bytes()).hexdigest()==r['sha256'],file
if '--record' in sys.argv:
 provenance={'job_id':os.environ.get('PBS_JOBID'),'runtime_commit':m['protected']['SIGN-qwen-history-window']['head'],'branch':'phase2/qwen-history-window','source_publication_manifest_sha256':m['source_publication_manifest_sha256'],'all_protected_sources_unchanged':True,'navigation_training_started':False,'resampling':False,'only_model':'Qwen3.5-2B','coverage32_evaluation_job_left_running':'1504280.stdct-mgmt-02'}
 (here/'review/audit/provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
print('Source guards passed')
