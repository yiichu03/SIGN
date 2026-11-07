"""Resident transport reused from SIGN qwen_reward.py @1256ca7.

Only the worker script is configurable; no rollout/reward imports are needed.
"""
import atexit
import json
import os
from pathlib import Path
import select
import subprocess

def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


class QwenClient:
    def __init__(self, cfg, output):
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.timeout = float(cfg.request_timeout)
        tree = Path(__file__).resolve().parents[1]
        env = dict(os.environ)
        env.pop('PYTHONPATH', None); env.pop('PYTHONHOME', None)
        env['PYTHONNOUSERSITE'] = '1'
        env['OMP_NUM_THREADS'] = env['MKL_NUM_THREADS'] = env['OPENBLAS_NUM_THREADS'] = '1'
        self.stderr = (self.output/'worker.log').open('w')
        command = [str(cfg.python_executable), '-u', str(tree/cfg.worker_script),
                   '--model-dir',str(cfg.model_dir), '--prompt',str((tree/cfg.prompt).resolve()),
                   '--output',str(self.output), '--verify',str(int(cfg.verify_first_batch))]
        if getattr(cfg, 'candidate_affordance', False):
            protocol = getattr(cfg,'candidate_protocol','abc')
            command += ['--task', protocol if protocol in ('semantic','directional') else 'candidate']
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=self.stderr, text=True, bufsize=1, env=env)
        atexit.register(self.close)
        self.boot = self._receive(float(cfg.startup_timeout))
        if not self.boot.get('ok') or self.boot.get('kind') != 'ready':
            raise RuntimeError('Qwen worker startup failed: '+str(self.boot))
        write_json(self.output/'worker_boot.json', self.boot)

    def _receive(self, timeout):
        ready, _, _ = select.select([self.process.stdout], [], [], timeout)
        if not ready:
            raise RuntimeError('Qwen worker timeout; inspect '+str(self.output/'worker.log'))
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError('Qwen worker exited unexpectedly; inspect '+str(self.output/'worker.log'))
        try:
            result = json.loads(line)
        except ValueError as exc:
            raise RuntimeError('Invalid Qwen worker protocol: '+line[:200]) from exc
        if not result.get('ok'):
            raise RuntimeError('Qwen worker error: '+str(result.get('error')))
        return result

    def score(self, request_id, rows):
        message = dict(kind='score', request_id=request_id, rows=rows)
        self.process.stdin.write(json.dumps(message, allow_nan=False)+'\n')
        self.process.stdin.flush()
        result = self._receive(self.timeout)
        if result.get('request_id') != request_id:
            raise RuntimeError('Qwen worker request ID mismatch')
        return result

    def close(self):
        p = getattr(self, 'process', None)
        if p is not None and p.poll() is None:
            try:
                p.stdin.write('{"kind":"close"}\n'); p.stdin.flush(); p.stdin.close()
                p.wait(timeout=10)
            except (OSError, subprocess.TimeoutExpired):
                p.terminate()
                try: p.wait(timeout=5)
                except subprocess.TimeoutExpired: p.kill(); p.wait()
        if hasattr(self, 'stderr') and not self.stderr.closed:
            self.stderr.close()
