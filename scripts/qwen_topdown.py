#!/usr/bin/env python3
"""Prepare/verify/run immutable offline Qwen image requests."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from qwen_topdown import prepare, verify, run

p = argparse.ArgumentParser(description=__doc__)
s = p.add_subparsers(dest='command', required=True)
a = s.add_parser('prepare');a.add_argument('--manifest', required=True);a.add_argument('--prompt', required=True);a.add_argument('--out', required=True);a.add_argument('--allow-unequal-steps', action='store_true')
a = s.add_parser('verify');a.add_argument('--request', required=True)
a = s.add_parser('run');a.add_argument('--request', required=True);a.add_argument('--out', required=True);a.add_argument('--config', default=str(Path(__file__).resolve().parents[1] / 'scripts/qwen_topdown_config.json'));a.add_argument('--enable', action='store_true')
args = p.parse_args()
if args.command == 'prepare':
    print(prepare(args.manifest, args.prompt, args.out, args.allow_unequal_steps))
elif args.command == 'verify':
    print(json.dumps(verify(args.request), ensure_ascii=False))
else:
    config = json.loads(Path(args.config).read_text())
    if args.enable:config['enabled'] = True
    print(json.dumps(run(args.request, args.out, config), ensure_ascii=False))
