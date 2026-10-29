"""All six case/milestone receipts are independently gated by exact SHA."""
import hashlib,importlib.util,json,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('watch_test',HERE/'watch_milestones.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);m.HERE=root;m.CKPT_ROOT=root/'ckpts'
    for case in ['A','B','C']:
        (root/case).mkdir();folder=m.CKPT_ROOT/case/'train/ckpts';folder.mkdir(parents=True)
        for step in [4608000,8192000]:
            p=folder/f'milestone_{step}.pth';p.write_bytes((case+str(step)).encode())
            p.with_suffix('.json').write_text(json.dumps(dict(step=step,path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())))
            with patch.object(m.argparse.ArgumentParser,'parse_args',return_value=SimpleNamespace(train_job='test',step=step,case=case)):
                with patch.object(m.subprocess,'run',side_effect=AssertionError('ready; should not query')):m.main()
            assert json.loads((root/case/f'val_{step}/checkpoint.json').read_text())['path']==str(p)
    p.write_bytes(b'corrupt')
    with patch.object(m.argparse.ArgumentParser,'parse_args',return_value=SimpleNamespace(train_job='test',step=8192000,case='C')):
        try:m.main()
        except AssertionError:pass
        else:raise AssertionError('Corrupted receipt accepted')
(HERE/'waiter_validation.json').write_text(json.dumps(dict(passed=True,case_milestones_verified=6,corrupt_checkpoint_rejected=True,pbs_mocked=True),indent=2)+'\n')
print('Six independent receipt paths and SHA checks passed')
