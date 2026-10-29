"""Exercise exact milestone saving and immutable receipt contents on CPU."""
import hashlib,json,sys,tempfile
from pathlib import Path
from types import SimpleNamespace
import torch
ROOT=Path('/scratch/e1538633/liuyi');sys.path.insert(0,str(ROOT/'SIGN-qwen-ablation'))
import run_sim
from src.trainer import PPOTrainer
with tempfile.TemporaryDirectory() as tmp:
    obj=PPOTrainer.__new__(PPOTrainer);obj._qwen_reward=object()
    obj.agent=SimpleNamespace(state_dict=lambda:dict(fixture=torch.tensor([1.,2.])))
    obj.config=SimpleNamespace(habitat_baselines=SimpleNamespace(checkpoint_folder=tmp))
    for step in (4608000,8192000):
        obj.save_checkpoint('ckpt.test.pth',dict(step=step))
        target=Path(tmp)/f'milestone_{step}.pth';receipt=json.loads(target.with_suffix('.json').read_text())
        assert receipt['step']==step and receipt['path']==str(target)
        assert receipt['sha256']==hashlib.sha256(target.read_bytes()).hexdigest()
        assert torch.load(str(target),map_location='cpu')['extra_state']['step']==step
        try:obj.save_checkpoint('ckpt.test.pth',dict(step=step))
        except RuntimeError as e:assert 'overwrite' in str(e)
        else:raise AssertionError('Milestone was overwritten')
report=dict(passed=True,actual_save_function_exercised=True,milestones=[4608000,8192000],sha_and_steps_verified=True,overwrite_rejected=True)
(ROOT/'logs/qwen_ablation_20261029/milestone_validation.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
