"""Check this independent worktree and protect the running frozen baseline."""
import hashlib
import json
from pathlib import Path

ROOT=Path('/scratch/e1538633/liuyi');TREE=ROOT/'SIGN-frozen-rollout-coverage';HERE=Path(__file__).resolve().parent
manifest=json.loads((HERE/'source_manifest.json').read_text())
for name,digest in manifest['files'].items():
    assert hashlib.sha256((TREE/name).read_bytes()).hexdigest()==digest, 'Coverage source changed: '+name
protected=json.loads((HERE/'original_worktree_before.json').read_text())
for name,digest in protected['files'].items():
    assert hashlib.sha256((ROOT/'SIGN'/name).read_bytes()).hexdigest()==digest, 'Original worktree changed: '+name
data=json.loads((ROOT/'manifests/gibson_reproduction_20261026.json').read_text())['splits']['train']
for item in data['files']:
    assert hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest()==item['sha256']
for name in data['scenes']:
    mesh=TREE/'data/scene_datasets/gibson'/name
    assert mesh.is_file() and mesh.with_suffix('.navmesh').is_file(), name
assert json.loads((HERE/'unit_results.json').read_text())['passed']
print('Coverage inputs and original frozen-training worktree verified',manifest['commit'],flush=True)
