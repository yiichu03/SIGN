"""Use the unchanged native evaluator and passive coverage telemetry, Qwen absent."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path('/scratch/e1538633/liuyi');HERE=Path(__file__).resolve().parent;TREE=ROOT/'SIGN-coverage-eval'
os.chdir(TREE);sys.path.insert(0,str(TREE));sys.path.insert(0,str(HERE))
import run_sim
import recording_env
from run_training import guard

def main():
    guard()
    import torch,numpy as np
    from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
    step=int(os.environ['QWEN_EVAL_STEP']);assert step in (4608000,8192000)
    out=HERE/f'val_{step}';manifest=json.loads((out/'checkpoint.json').read_text());path=Path(manifest['path'])
    assert hashlib.sha256(path.read_bytes()).hexdigest()==manifest['sha256']
    ckpt=torch.load(str(path),map_location='cpu');assert ckpt['extra_state']['step']==step
    assert os.environ['PYTHONHASHSEED']=='0' and os.environ.get('PBS_JOBID') and torch.cuda.is_available()
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=TREE,text=True).strip()==json.loads((HERE/'source_manifest.json').read_text())['trees']['SIGN-coverage-eval']['commit']
    os.environ['COVERAGE_EVAL_EPISODES']=str(out/'episodes')
    opts=['habitat_baselines.eval_ckpt_path_dir',str(path),'habitat.env_task','CoverageEvalGym','habitat.task.observed_coverage.weight','0.0']
    config='exp_config/ppo_imagenav_gibson.yaml,policy,reward,sensors,eval,rollout_coverage'
    started=time.time()
    run_sim.run_exp(exp_config=config,run_type='eval',opts=opts,model_dir=str(out/'native'),overwrite=False,note='',debug=False)
    expected={tuple(k) for k in json.loads((HERE/'eval_protocol.json').read_text())['episode_keys']}
    rows={}
    for p in (out/'episodes').glob('*.jsonl'):
        for line in p.read_text().splitlines():
            r=json.loads(line);key=(r['scene_id'],r['episode_id']);assert key not in rows;rows[key]=r
    assert set(rows)==expected and len(rows)==4200
    assert all(r['steps']>0 and all(np.isfinite(r[k]) for k in ['success','spl','new_area_m2','new_m2_per_step','navigation_reward']) for r in rows.values())
    ea=EventAccumulator(str(out/'native/tb'),size_guidance={'scalars':0});ea.Reload()
    native={t:ea.Scalars(t)[-1].value for t in ea.Tags()['scalars']}
    assert all(ea.Scalars(t)[-1].step==step for t in native)
    result=dict(training_step=step,episodes=4200,scenes=14,success_rate=float(np.mean([r['success'] for r in rows.values()])),
        spl=float(np.mean([r['spl'] for r in rows.values()])),new_m2_per_step_global=sum(r['new_area_m2'] for r in rows.values())/sum(r['steps'] for r in rows.values()),
        mean_episode_new_m2_per_step=float(np.mean([r['new_m2_per_step'] for r in rows.values()])),native_metrics=native,
        seconds=time.time()-started,qwen_enabled=False,qwen_trajectory_collection=False,
        protocol='Original deterministic 4200 Gibson val /6 env/max500/seed100/hash0; passive 0.1m/3m/90deg coverage, weight0')
    assert all(np.isfinite(v) for v in native.values())
    assert abs(native['eval_metrics/success']-result['success_rate'])<1e-5
    assert abs(native['eval_metrics/spl']-result['spl'])<1e-5
    guard()
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
