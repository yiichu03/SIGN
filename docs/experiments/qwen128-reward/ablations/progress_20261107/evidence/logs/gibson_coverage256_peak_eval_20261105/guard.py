"""Read-only checks for unchanged evaluator, training sources and fixed inputs."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path('/scratch/e1538633/liuyi');HERE=Path(__file__).resolve().parent

def guard():
    m=json.loads((HERE/'source_manifest.json').read_text())
    for name,item in m['trees'].items():
        tree=ROOT/name
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=tree,text=True).strip()==item['commit'],name
        for name,digest in item['files'].items():assert hashlib.sha256((tree/name).read_bytes()).hexdigest()==digest
    for name,digest in m['assets'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    for name,digest in m.get('support_scripts',{}).items():assert hashlib.sha256((HERE/name).read_bytes()).hexdigest()==digest
    for case in json.loads((HERE/'manifest.json').read_text())['cases'].values():
        assert hashlib.sha256(Path(case['path']).read_bytes()).hexdigest()==case['sha256']
