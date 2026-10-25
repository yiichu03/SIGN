"""Read-only evidence checks and a non-destructive publication plan (stdlib only)."""
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def load(path):
    return json.loads(path.read_text())


def within(path, parent):
    return path == parent or parent in path.parents


def audit_pilot(root):
    """Check saved evidence; never run inference, summarize, or repair an answer."""
    from qwen_pairwise_diagnostic import parse, canonical, readable_preference, read_human

    manifest = load(root / 'manifest.json')
    requests = load(root / 'requests.json')
    reference = load(root / 'human_labels_frozen.json')
    labels = reference['labels']
    for filename, field in [('human_labels_frozen.md', 'human_markdown_sha256'),
                            ('manifest.json', 'manifest_sha256'), ('requests.json', 'requests_sha256')]:
        require(sha((root / filename).read_bytes()) == reference[field], f'Frozen reference changed: {filename}')
    require(read_human(root / 'human_labels_frozen.md') == labels, 'Frozen human JSON differs from its Markdown.')
    require((root / 'human_labels.md').read_bytes() == (root / 'human_labels_frozen.md').read_bytes(),
            'Human labels differ from the frozen version; preserve and version the revision before publication.')
    pairs = {p['id']: p for p in manifest['pairs']}
    require(len(pairs) == 24 and set(labels) == set(pairs), 'Expected 24 frozen pair references.')
    expected = {f'{p["id"]}_{mode}_{variant}' for p in pairs.values() for mode in ('A0', 'A1')
                for variant in (('normal', 'swapped') if p['swap'] else ('normal',))}
    require(len(requests) == len(expected) == manifest['planned_requests'] == 64, 'Expected all 64 planned requests.')
    require({r['id'] for r in requests} == expected, 'Request identities do not match the pair manifest.')
    require({p.name for p in (root / 'model_requests').iterdir() if p.is_dir()} == expected,
            'Unexpected or missing request directories; do not silently include another run.')
    strict = load(root / 'comparison.json')
    readable = load(root / 'decision_diagnostics.json')
    strict_rows = {r['id']: r for r in strict['requests']}
    readable_rows = {r['id']: r for r in readable['requests']}
    require(len(strict['requests']) == len(readable['requests']) == 64 and
            set(strict_rows) == set(readable_rows) == expected, 'Statistics must cover exactly the same 64 requests.')
    for spec in requests:
        pair = pairs[spec['pair']]
        folder = root / 'model_requests' / spec['id']
        require(load(folder / 'input.json') == spec, f'Input metadata differs: {spec["id"]}')
        require(sha((folder / 'request.txt').read_bytes()) == spec['request_sha256'], f'Request hash differs: {spec["id"]}')
        result = load(folder / 'result.json')
        require(result['request_sha256'] == spec['request_sha256'], f'Result input hash differs: {spec["id"]}')
        raw = (folder / 'response.txt').read_text()
        parsed, error = parse(raw)
        require(parsed == result['parsed'] and error == result['parse_error'], f'Saved strict parse differs: {spec["id"]}')
        preference = canonical(parsed['preference'], spec) if parsed else None
        require(result['canonical_preference'] == preference == strict_rows[spec['id']]['canonical_preference'],
                f'Strict decision differs: {spec["id"]}')
        saved = strict_rows[spec['id']]
        require(saved['parsed'] == parsed and saved['parse_error'] == error and
                saved['request_sha256'] == spec['request_sha256'] and saved['human'] == labels[spec['pair']]['preference'],
                f'Strict evidence or reference differs: {spec["id"]}')
        row = readable_rows[spec['id']]
        require(row['raw_response_sha256'] == sha((folder / 'response.txt').read_bytes()), f'Raw response changed: {spec["id"]}')
        require(row['readable_canonical'] == canonical(readable_preference(raw), spec) and
                row['strict_canonical'] == preference and row['human'] == labels[spec['pair']]['preference'],
                f'Readable decision or human reference differs: {spec["id"]}')
        order = 'BA' if spec['variant'] == 'swapped' else 'AB'
        require(spec['shown_A_original'] == order[0] and spec['shown_B_original'] == order[1], f'Wrong presentation order: {spec["id"]}')
        require(spec['source_sha256'] == pair['source_sha256'], f'Trajectory hashes differ: {spec["id"]}')
        for side in 'AB':
            require(sha((root / pair['id'] / f'{side}_waypoints.json').read_bytes()) == pair['source_sha256'][side],
                    f'Trajectory changed: {pair["id"]}/{side}')
        images = spec['images']
        require(len(images) == (2 if spec['condition'] == 'A1' else 0), f'Wrong image count: {spec["id"]}')
        for shown, side, image in zip('AB', order, images):
            source = root / pair['id'] / f'{side}_overview.png'
            require(image['shown_as'] == shown and Path(image['path']).resolve() == source.resolve() and
                    image['sha256'] == sha(source.read_bytes()), f'Image/order hash differs: {spec["id"]}')
    for mode in ('A0', 'A1'):
        normal = [r for r in readable_rows.values() if r['condition'] == mode and r['variant'] == 'normal']
        lookup = {r['pair']: r for r in normal}
        swaps = [r for r in readable_rows.values() if r['condition'] == mode and r['variant'] == 'swapped']
        summary = readable['summary'][mode]
        for field, key in [('strict', 'strict_canonical'), ('readable', 'readable_canonical')]:
            valid_swaps = [r for r in swaps if r[key] is not None and lookup[r['pair']][key] is not None]
            require(summary[field + '_agreement'] == sum(r[key] == r['human'] for r in normal), f'{mode} agreement differs.')
            require(summary[field + '_swap_valid'] == len(valid_swaps) and summary[field + '_swap_consistent'] ==
                    sum(r[key] == lookup[r['pair']][key] for r in valid_swaps), f'{mode} swap statistics differ.')
        require(summary['normal_requests'] == 24 and summary['strict_valid'] == sum(r['strict_canonical'] is not None for r in normal),
                f'{mode} validity differs.')
        require(summary['strict_agreement'] == strict['summary'][mode]['agreement_with_known_human'] and
                strict['summary'][mode]['invalid'] == 24 - summary['strict_valid'] and
                strict['summary'][mode]['valid_swaps'] == summary['strict_swap_valid'] and
                strict['summary'][mode]['swap_consistent'] == summary['strict_swap_consistent'], f'{mode} strict summary differs.')
        require(summary['readable_distribution'] == {v: sum(r['readable_canonical'] == v for r in normal)
                for v in ('A_LESS', 'B_LESS', 'TIE', 'UNKNOWN')}, f'{mode} preference distribution differs.')
    state = load(root / 'model_run.json')
    require(state['status'] == 'complete', 'The completed pilot must retain its complete run record.')
    return dict(pairwise_requests=64, pairwise_request_files=256, human_pairs=len(labels),
                human_counts=dict(Counter(v['preference'] for v in labels.values())), summary=readable['summary'])


class Publication:
    """Build bytes in memory, validate everything, then write changed files only."""
    allowed_suffixes = {'.py', '.yaml', '.yml', '.md', '.txt', '.sh', '.cfg', '.toml', '.msg',
                        '.launch', '.pbs', '.patch', '.json', '.jsonl', '.csv', '.png', '.gif'}
    forbidden_parts = {'data', 'ckpt', 'checkpoints', 'envs', 'models', '__pycache__', '.git', '.aws', '.ssh', '.codex', '.agents'}
    workspace_documents = ('AGENTS.md', 'STATUS.md', 'RUNBOOK.md', 'WORKLOG.md')

    def __init__(self, root):
        self.root = root.resolve()
        self.entries = {}
        status = self.root / 'status.json'
        self.timestamp = load(status)['snapshot_at'] if status.exists() else datetime.now(timezone.utc).isoformat()

    def add(self, path, data):
        path = path.resolve()
        require(self.root in path.parents, f'Publication path escapes the bundle: {path}')
        relative = path.relative_to(self.root)
        require(not (set(relative.parts) & self.forbidden_parts), f'Excluded directory: {relative}')
        require(path.suffix in self.allowed_suffixes or path.name == '.gitignore', f'Excluded file type: {relative}')
        data = data.encode('utf-8') if isinstance(data, str) else data
        require(len(data) <= 5 * 1024**2, f'File exceeds 5 MiB: {relative}; review before publishing.')
        require(relative not in self.entries or self.entries[relative] == data, f'Conflicting copies: {relative}')
        self.entries[relative] = data

    def verify_existing(self):
        manifest_path = self.root / 'publication_manifest.json'
        require(manifest_path.exists(), 'Expected the existing publication manifest; do not recreate a missing archive.')
        manifest = load(manifest_path)
        listed = {Path(f['path']) for f in manifest['files']}
        actual = {p.relative_to(self.root) for p in self.root.rglob('*') if p.is_file() and p != manifest_path}
        require(listed == actual, 'Archive files differ from its manifest; inspect missing or extra records before publishing.')
        for record in manifest['files']:
            path = self.root / record['path']
            require(within(path.resolve(), self.root), f'Archive path escapes the bundle: {path}')
            data = path.read_bytes()
            require(len(data) == record['bytes'] and sha(data) == record['sha256'],
                    f'Published file differs from its manifest: {record["path"]}; preserve the edit and reconcile explicitly.')
            relative = Path(record['path'])
            require(relative in self.entries, f'An archived record is missing from the new plan: {relative}; no deletion performed.')
            workspace_document = (len(relative.parts) == 2 and relative.parts[0] == 'workspace' and
                                  relative.name in self.workspace_documents)
            if relative == Path('workspace/WORKLOG.md'):
                require(self.entries[relative].startswith(data),
                        'Published WORKLOG is append-only; preserve earlier entries and append corrections.')
            mutable = (relative.parts[0] == 'code' or workspace_document or
                       str(relative) in {'README.md', 'pilot/README.md', 'status.json'})
            require(mutable or self.entries[relative] == data,
                    f'Existing evidence/review would change: {relative}; preserve it and version the change separately.')

    def verify_links(self):
        for relative, data in self.entries.items():
            if relative.suffix != '.md':
                continue
            for href in re.findall(r'\[[^\[\]]*\]\(([^\s)]+)\)', data.decode('utf-8')):
                if href.startswith(('http://', 'https://', '/', '#', 'mailto:')) or '{{' in href:
                    continue
                filename = href.split('#', 1)[0]
                target = (self.root / relative.parent / filename).resolve()
                if self.root in target.parents:
                    target_relative = target.relative_to(self.root)
                    require(target_relative == Path('publication_manifest.json') or target_relative in self.entries or
                            any(target_relative in p.parents for p in self.entries),
                            f'Broken relative link: {relative} -> {href}')
                else:
                    require(target.exists() and within(target, self.root.parent.parent.parent), f'Broken/external local link: {relative} -> {href}')
                if href.endswith('#本地目录与-git-结构'):
                    require(b'## ' + '本地目录与 Git 结构'.encode() in self.entries[target.relative_to(self.root)], f'Missing section: {href}')

    def finish(self, base_commit, audit, check_only=False):
        self.verify_existing()
        self.verify_links()
        require(sum(len(data) for data in self.entries.values()) <= 100 * 1024**2, 'Bundle exceeds 100 MiB; review its scope.')
        changed = [p for p, data in self.entries.items() if not (self.root / p).exists() or (self.root / p).read_bytes() != data]
        print(f'Evidence verified: {audit["pairwise_requests"]}/64 requests, 256 request files, '
              f'{audit["history_outputs"]} historical prompt outputs, {audit["group8_outputs"]} group8 outputs.')
        if not changed:
            print('Publication is already current; no files or timestamps changed.')
            return []
        stamp = datetime.now(timezone.utc).isoformat()
        self.entries[Path('README.md')] = self.entries[Path('README.md')].replace(self.timestamp.encode(), stamp.encode(), 1)
        state = json.loads(self.entries[Path('status.json')])
        state['snapshot_at'] = stamp
        self.entries[Path('status.json')] = (json.dumps(state, ensure_ascii=False, indent=2) + '\n').encode()
        files = [dict(path=str(p), bytes=len(data), sha256=sha(data)) for p, data in sorted(self.entries.items())]
        manifest = dict(created_at=stamp, sign_base_commit=base_commit, files=files,
                        total_bytes=sum(f['bytes'] for f in files), verification=audit)
        self.entries[Path('publication_manifest.json')] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
        changed = [p for p, data in self.entries.items() if not (self.root / p).exists() or (self.root / p).read_bytes() != data]
        print('Planned publication changes:')
        for p in sorted(changed):
            print('  ' + str(p))
        if not check_only:
            for p in changed:
                target = self.root / p
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(self.entries[p])
            for p, data in self.entries.items():
                require(sha((self.root / p).read_bytes()) == sha(data), f'Write verification failed: {p}')
            print(f'Published {len(files)} files, {manifest["total_bytes"]} bytes; hashes verified. No files deleted.')
        return changed
