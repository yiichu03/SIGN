#!/usr/bin/env python3
"""Generate evidence/root-document copies; no Git writes or PBS submissions."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
TREE=Path(__file__).resolve().parents[1];ROOT=TREE.parent
DEST=TREE/'docs/experiments/qwen-memory-four-arm'
BATCH=ROOT/'logs/qwen_memory_four_arm_20261108'


def main():
    evidence=DEST/'evidence';evidence.mkdir(exist_ok=True)
    mapping={};manifest={}
    def copy(source):
        source=Path(source)
        target=evidence/source.relative_to(BATCH)
        target.parent.mkdir(parents=True,exist_ok=True)
        raw=source.read_bytes();target.write_bytes(raw);mapping[str(source)]=target
        manifest[str(target.relative_to(DEST))]=dict(source=str(source),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
        return target
    for name in ['retrieval_qa.json','config_preflight.json','legacy_tests.txt','new_tests.txt','single_tests.txt','review_smoke.py','review_smoke.json']:
        copy(BATCH/name)
    for folder in ['smoke_5799fc9','smoke_057740b']:
        b=BATCH/folder
        for name in ['submission.json','source_manifest.json','tasks.json','probe_inputs.json','multi_image_probe.json','smoke_summary.json']:
            if (b/name).exists():copy(b/name)
        for path in sorted((b/'worker_probe').glob('*.json')):copy(path)
        for path in sorted(b.glob('smoke_*/result.json')):copy(path)
        for name in ['memory.jsonl','events.jsonl','feedback.jsonl','outcomes.jsonl','episodes.jsonl','summary.json']:
            for path in sorted(b.glob('smoke_*/native/recovery/'+name)):copy(path)
        for path in sorted(b.glob('smoke_*/native/recovery/worker/*.json')):copy(path)
    for name in ['smoke_vs_rule','smoke_vs_A']:
        for path in (BATCH/name).glob('*'):
            if path.suffix in ('.json','.csv'):copy(path)
    # Portable, bounded true model inputs referenced by the direct technical probe.
    probe=BATCH/'smoke_057740b/multi_image_probe.json'
    if probe.exists():
        inputs=json.loads(probe.read_text())['inputs'];seen=set()
        for row in inputs:
            for item in row['images']:
                source=Path(item['image']);digest=hashlib.sha256(source.read_bytes()).hexdigest()
                assert digest==item['image_sha256']
                target=evidence/'images'/(digest[:16]+'.png')
                if digest not in seen:
                    target.parent.mkdir(exist_ok=True);shutil.copyfile(source,target);seen.add(digest)
                    manifest[str(target.relative_to(DEST))]=dict(source=str(source),sha256=digest,bytes=target.stat().st_size)
                mapping[str(source)]=target
    workspace=DEST/'workspace';workspace.mkdir(exist_ok=True)
    for name in ['AGENTS.md','STATUS.md','RUNBOOK.md','WORKLOG.md']:mapping[str(ROOT/name)]=workspace/name
    for name in ['AGENTS.md','STATUS.md','RUNBOOK.md','WORKLOG.md']:
        source=ROOT/name;target=workspace/name;raw=source.read_bytes()
        if name=='WORKLOG.md':
            if target.exists():assert raw.startswith(target.read_bytes()),'Published WORKLOG must remain append-only'
            output=raw
        else:
            def portable(match):
                marker,label,url=match.groups()
                if url.startswith(('https:','http:','#','mailto:')):return match.group(0)
                path,sep,anchor=url.strip('<>').partition('#');absolute=Path(path) if path.startswith('/') else ROOT/path
                mapped=mapping.get(str(absolute))
                if mapped is None:
                    try:
                        candidate=TREE/absolute.relative_to(TREE)
                        if candidate.exists():mapped=candidate
                    except ValueError:pass
                if mapped is None:return label+'（服务器：`'+str(absolute)+'`）'
                return marker+'['+label+']('+os.path.relpath(mapped,target.parent)+(sep+anchor if sep else '')+')'
            output=re.sub(r'(!?)\[([^\]]*)\]\(([^)]+)\)',portable,raw.decode()).encode()
        target.write_bytes(output)
        manifest[str(target.relative_to(DEST))]=dict(source=str(source),source_sha256=hashlib.sha256(raw).hexdigest(),
            sha256=hashlib.sha256(output).hexdigest(),bytes=len(output),encoding='verbatim' if name=='WORKLOG.md' else 'portable_links')
    (DEST/'inputs.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Generated',len(manifest),'evidence/document copies; no jobs submitted')

if __name__=='__main__':main()
