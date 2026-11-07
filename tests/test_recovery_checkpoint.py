import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from recovery_checkpoint import validate_checkpoint


class CheckpointIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.model = self.root/'model.pth'; self.model.write_bytes(b'coverage checkpoint')
        self.digest = hashlib.sha256(self.model.read_bytes()).hexdigest()
        self.cached = dict(step=125952000, sha256=self.digest)
        self.result = dict(training_step=125952000, episodes=4200)
        self.write_cached()
        self.tasks = dict(checkpoint=dict(step=125952000, path=str(self.model), sha256=self.digest),
            reference=dict(directory=str(self.root), training_step=125952000, checkpoint_sha256=self.digest))

    def write_cached(self):
        (self.root/'checkpoint.json').write_text(json.dumps(self.cached))
        (self.root/'result.json').write_text(json.dumps(self.result))

    def test_accepts_matching_model_and_complete_reference(self):
        self.assertEqual(validate_checkpoint(self.tasks, 125952000), self.root)

    def test_rejects_frozen_baseline_model_step(self):
        with self.assertRaisesRegex(ValueError, 'Loaded checkpoint step'):
            validate_checkpoint(self.tasks, 74240000)

    def test_rejects_reference_to_a_different_step(self):
        self.tasks['reference']['training_step'] = 74240000
        with self.assertRaisesRegex(ValueError, 'different training step'):
            validate_checkpoint(self.tasks, 125952000)

    def test_rejects_changed_model_bytes(self):
        self.model.write_bytes(b'wrong checkpoint')
        with self.assertRaisesRegex(ValueError, 'SHA mismatch'):
            validate_checkpoint(self.tasks, 125952000)

    def test_rejects_a_different_cached_checkpoint(self):
        self.cached['sha256'] = '0'*64; self.write_cached()
        with self.assertRaisesRegex(ValueError, 'different checkpoint'):
            validate_checkpoint(self.tasks, 125952000)

    def test_rejects_incomplete_reference(self):
        self.result['episodes'] = 2652; self.write_cached()
        with self.assertRaisesRegex(ValueError, 'complete 4200'):
            validate_checkpoint(self.tasks, 125952000)


if __name__ == '__main__':
    unittest.main()
