"""Test exact receipt gating for the pre-submitted PBS afterok evaluations."""
import hashlib,importlib.util,json,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('watch_test',HERE/'watch_milestones.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);m.HERE=root;m.CKPT=root/'ckpts';m.CKPT.mkdir()
    for step in (4608000,8192000):
        p=m.CKPT/f'milestone_{step}.pth';p.write_bytes(str(step).encode())
        p.with_suffix('.json').write_text(json.dumps(dict(step=step,path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())))
        with patch.object(m.argparse.ArgumentParser,'parse_args',return_value=SimpleNamespace(train_job='test',step=step)):
            with patch.object(m.subprocess,'run',side_effect=AssertionError('receipt ready; no polling')):
                m.main();m.main()
        assert json.loads((root/f'val_{step}/wait_state.json').read_text())['ready']
        assert json.loads((root/f'val_{step}/checkpoint.json').read_text())['step']==step
    step=8192000;p=m.CKPT/f'milestone_{step}.pth';p.write_bytes(b'corrupted')
    with patch.object(m.argparse.ArgumentParser,'parse_args',return_value=SimpleNamespace(train_job='test',step=step)):
        try:m.main()
        except AssertionError:pass
        else:raise AssertionError('Corrupt checkpoint accepted')
(HERE/'watcher_validation.json').write_text(json.dumps(dict(passed=True,both_exact_milestones_tested=True,corrupt_checkpoint_rejected=True,idempotent_receipt=True,real_pbs_submission=False,protocol='GPU eval pre-submitted with afterok dependency on this CPU waiter'),indent=2)+'\n')
print('PBS prerequisite checkpoint metadata/hash gating passed')
