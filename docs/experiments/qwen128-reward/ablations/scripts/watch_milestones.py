"""CPU prerequisite job: release a pre-submitted eval only after its exact checkpoint."""
import argparse,datetime,hashlib,json,os,subprocess,time
from pathlib import Path
ROOT=Path('/scratch/e1538633/liuyi');HERE=Path(__file__).resolve().parent
CKPT_ROOT=ROOT/'SIGN-qwen-ablation/results/qwen_ablation_20261029'
def stamp():return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='seconds')
def write(path,value):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(path)
def main():
    p=argparse.ArgumentParser();p.add_argument('--train-job',required=True);p.add_argument('--step',type=int,required=True);p.add_argument('--case',choices=['A','B','C'],required=True)
    a=p.parse_args();assert a.step in (4608000,8192000)
    CKPT=CKPT_ROOT/a.case/'train/ckpts'
    out=HERE/a.case/f'val_{a.step}';out.mkdir(exist_ok=True);sidecar=CKPT/f'milestone_{a.step}.json'
    while True:
        m=None
        if sidecar.exists():
            try:m=json.loads(sidecar.read_text())
            except json.JSONDecodeError:
                if time.time()-sidecar.stat().st_mtime>=120:raise
        if m is not None:
            assert m['step']==a.step and m['path']==str(CKPT/f'milestone_{a.step}.pth')
            assert hashlib.sha256(Path(m['path']).read_bytes()).hexdigest()==m['sha256']
            # Immutable checkpoint has been completely written and checked. Exiting 0
            # releases the GPU eval's PBS afterok dependency, without compute-node qsub.
            write(out/'checkpoint.json',m)
            write(out/'wait_state.json',dict(ready=True,train_job=a.train_job,step=a.step,at=stamp(),wait_job=os.environ.get('PBS_JOBID')))
            print('READY',a.step,m['sha256'],flush=True);return
        write(out/'wait_state.json',dict(ready=False,train_job=a.train_job,step=a.step,at=stamp(),wait_job=os.environ.get('PBS_JOBID')))
        try:
            state=subprocess.run(['qstat','-fx',a.train_job],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=15)
            if 'job_state = F' in state.stdout:
                raise RuntimeError('Training ended before milestone '+str(a.step)+'; '+state.stdout[-1000:])
            if state.returncode:print('Scheduler query unavailable; continue checkpoint polling',flush=True)
        except subprocess.TimeoutExpired:
            print('Scheduler query timeout; continue checkpoint polling',flush=True)
        time.sleep(60)
if __name__=='__main__':main()
