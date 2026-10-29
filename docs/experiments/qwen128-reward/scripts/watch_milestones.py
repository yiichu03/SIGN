"""CPU prerequisite job: release a pre-submitted eval only after its exact checkpoint."""
import argparse,datetime,hashlib,json,os,subprocess,time
from pathlib import Path
ROOT=Path('/scratch/e1538633/liuyi');HERE=Path(__file__).resolve().parent
CKPT=ROOT/'SIGN-qwen128-reward/results/qwen128_reward_20261029/train_personal_8env/ckpts'
def stamp():return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='seconds')
def write(path,value):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(path)
def main():
    p=argparse.ArgumentParser();p.add_argument('--train-job',required=True);p.add_argument('--step',type=int,required=True)
    a=p.parse_args();assert a.step in (4608000,8192000)
    out=HERE/f'val_{a.step}';out.mkdir(exist_ok=True);sidecar=CKPT/f'milestone_{a.step}.json'
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
        state=subprocess.run(['qstat','-fx',a.train_job],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        if 'job_state = F' in state.stdout or state.returncode:
            raise RuntimeError('Training ended before milestone '+str(a.step)+'; '+state.stdout[-1000:])
        time.sleep(60)
if __name__=='__main__':main()
