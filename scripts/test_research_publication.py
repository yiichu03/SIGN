"""CPU safety regression checks; fixtures live in /tmp, no experiment is run."""
import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from research_publication import Publication, audit_pilot, sha
from publish_relative_diagnostic import LEGACY_DOCUMENTS, add_workspace_snapshot

ROOT = Path(__file__).resolve().parents[1]
AUDIT = dict(pairwise_requests=64, history_outputs=3600, group8_outputs=80)


class PublicationSafetyTests(unittest.TestCase):
    def fixture(self, override=None):
        root = Path(tempfile.mkdtemp(prefix='sign-publication-test-'))
        entries = {Path('README.md'): b'# Research\n2026-10-14T00:00:00+00:00\n',
                   Path('status.json'): b'{"snapshot_at":"2026-10-14T00:00:00+00:00"}\n',
                   Path('pilot/model_review.md'): b'Original human review\n'}
        records = []
        for relative, data in entries.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            records.append(dict(path=str(relative), bytes=len(data), sha256=sha(data)))
        (root / 'publication_manifest.json').write_text(json.dumps(dict(files=records)))
        publication = Publication(root)
        for relative, data in entries.items():
            publication.add(root / relative, (override or {}).get(relative, data))
        return root, publication

    def existing_workspace_record(self, relative, old, new):
        root, publication = self.fixture()
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(old)
        manifest_path = root / 'publication_manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['files'].append(dict(path=relative, bytes=len(old), sha256=sha(old)))
        manifest_path.write_text(json.dumps(manifest))
        publication.add(path, new)
        return publication

    def test_workspace_export_keeps_retired_snapshot_docs_without_source_copies(self):
        root = Path(tempfile.mkdtemp(prefix='sign-workspace-export-test-'))
        workspace, output = root / 'server', root / 'bundle'
        workspace.mkdir()
        for name in Publication.workspace_documents:
            (workspace / name).write_text('# ' + name + '\n')
        for relative in LEGACY_DOCUMENTS:
            path = output / 'code' / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('Archived ' + str(relative) + '\n')
        publication = Publication(output)
        add_workspace_snapshot(publication, workspace, output)
        self.assertEqual(len(publication.entries), 7)
        self.assertFalse((workspace / 'SIGN/AGENTS.md').exists())
        for name in Publication.workspace_documents:
            self.assertEqual(publication.entries[Path('workspace') / name], (workspace / name).read_bytes())
        for relative in LEGACY_DOCUMENTS:
            self.assertEqual(publication.entries[Path('code') / relative], (output / 'code' / relative).read_bytes())

    def test_missing_workspace_document_stops_without_writing_exports(self):
        root = Path(tempfile.mkdtemp(prefix='sign-workspace-missing-test-'))
        workspace, output = root / 'server', root / 'bundle'
        workspace.mkdir()
        (workspace / 'AGENTS.md').write_text('# Rules\n')
        with self.assertRaisesRegex(RuntimeError, 'Missing workspace document'):
            add_workspace_snapshot(Publication(output), workspace, output)
        self.assertFalse(output.exists())

    def test_published_worklog_accepts_appended_entries(self):
        old = b'# Log\n\n2026-10-26T01:00:00+08:00 first entry\n'
        publication = self.existing_workspace_record('workspace/WORKLOG.md', old, old + b'Next entry\n')
        publication.verify_existing()

    def test_published_worklog_rejects_rewrites_and_truncation(self):
        old = b'# Log\nOriginal entry\n'
        for new in (b'# Log\nRewritten entry\n', old[:-1], b''):
            with self.subTest(new=new):
                publication = self.existing_workspace_record('workspace/WORKLOG.md', old, new)
                with self.assertRaisesRegex(RuntimeError, 'WORKLOG is append-only'):
                    publication.verify_existing()

    def test_workspace_status_can_change_but_other_evidence_cannot(self):
        self.existing_workspace_record('workspace/STATUS.md', b'Old status\n', b'New status\n').verify_existing()
        publication = self.existing_workspace_record('workspace/evidence.md', b'Original\n', b'Replaced\n')
        with self.assertRaisesRegex(RuntimeError, 'Existing evidence/review would change'):
            publication.verify_existing()

    def test_existing_human_review_cannot_be_overwritten(self):
        root, publication = self.fixture({Path('pilot/model_review.md'): b'Replacement review\n'})
        with self.assertRaisesRegex(RuntimeError, 'Existing evidence/review would change'):
            publication.verify_existing()
        self.assertEqual((root / 'pilot/model_review.md').read_bytes(), b'Original human review\n')

    def test_published_manual_edit_stops_before_overwrite(self):
        root, publication = self.fixture()
        review = root / 'pilot/model_review.md'
        review.write_text('Original human review\nNew annotation\n')
        with self.assertRaisesRegex(RuntimeError, 'differs from its manifest'):
            publication.verify_existing()
        self.assertIn('New annotation', review.read_text())

    def test_missing_planned_history_record_stops(self):
        root, publication = self.fixture()
        publication.entries.pop(Path('pilot/model_review.md'))
        with self.assertRaisesRegex(RuntimeError, 'missing from the new plan'):
            publication.verify_existing()
        self.assertTrue((root / 'pilot/model_review.md').exists())

    def test_weights_cache_and_path_escape_are_rejected(self):
        root, publication = self.fixture()
        for path in (root / 'weights.pth', root / 'code/__pycache__/test.pyc', root.parent / 'outside.md'):
            with self.subTest(path=path), self.assertRaises(RuntimeError):
                publication.add(path, b'excluded')

    def test_broken_markdown_link_stops(self):
        root, publication = self.fixture({Path('README.md'): b'[Missing](missing.md)\n'})
        with self.assertRaisesRegex(RuntimeError, 'Broken relative link'):
            publication.verify_links()

    def test_directory_links_accept_planned_source_files(self):
        root, publication = self.fixture({Path('README.md'): b'[Source](code/src/)\n[Manifest](publication_manifest.json)\n'})
        publication.add(root / 'code/src/policy.py', b'# Source\n')
        publication.verify_links()

    def test_preview_does_not_write(self):
        root, publication = self.fixture({Path('README.md'): b'# Updated Research\n'})
        before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(publication.finish('base', AUDIT, check_only=True))
        self.assertEqual(before, {p: p.read_bytes() for p in root.rglob('*') if p.is_file()})

    def test_no_change_preserves_manifest_and_timestamps(self):
        root, publication = self.fixture()
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()}
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(publication.finish('base', AUDIT), [])
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()})

    def test_wrong_branch_stops_before_publication(self):
        root = Path(tempfile.mkdtemp(prefix='sign-sync-branch-test-'))
        source = root / 'SIGN/scripts'
        target = root / 'SIGN-SRU-reward-review'
        source.mkdir(parents=True)
        target.mkdir()
        script = source / 'sync_research_github.sh'
        script.write_bytes((ROOT / 'scripts/sync_research_github.sh').read_bytes())
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(target)], check=True)
        result = subprocess.run(['bash', str(script), '--check-only'], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Wrong publication branch', result.stderr)
        self.assertFalse((target / 'docs').exists())

    def test_wrong_remote_stops_before_fetch(self):
        root = Path(tempfile.mkdtemp(prefix='sign-sync-remote-test-'))
        source = root / 'SIGN/scripts'
        target = root / 'SIGN-SRU-reward-review'
        source.mkdir(parents=True)
        target.mkdir()
        script = source / 'sync_research_github.sh'
        script.write_bytes((ROOT / 'scripts/sync_research_github.sh').read_bytes())
        subprocess.run(['git', 'init', '-q', '-b', 'docs/qwen-reward-review-20261013', str(target)], check=True)
        subprocess.run(['git', '-C', str(target), 'remote', 'add', 'origin', 'https://example.invalid/wrong.git'], check=True)
        result = subprocess.run(['bash', str(script), '--check-only'], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('origin must be yiichu03/SIGN-SRU', result.stderr)
        self.assertFalse((target / '.git/FETCH_HEAD').exists())

    def test_git_check_preserves_original_csv_crlf(self):
        root = Path(tempfile.mkdtemp(prefix='sign-csv-crlf-test-'))
        subprocess.run(['git', 'init', '-q', str(root)], check=True)
        raw = b'case,label\r\nepisode_001,NONE\r\n'
        (root / 'original.csv').write_bytes(raw)
        subprocess.run(['git', '-C', str(root), '-c', 'core.autocrlf=false', 'add', 'original.csv'], check=True)
        subprocess.run(['git', '-C', str(root), '-c', 'core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol',
                        'diff', '--cached', '--check'], check=True)
        stored = subprocess.check_output(['git', '-C', str(root), 'show', ':original.csv'])
        self.assertEqual(stored, raw)

    def test_actual_64_request_evidence(self):
        result = audit_pilot(ROOT / 'results/qwen_diagnostic/pairwise_pilot_20261013')
        self.assertEqual(result['pairwise_request_files'], 256)
        self.assertEqual(result['summary']['A0']['strict_agreement'], 6)
        self.assertEqual(result['summary']['A1']['readable_agreement'], 9)


if __name__ == '__main__':
    unittest.main(verbosity=2)
