"""Resident-process client and rollout settlement. The training env imports no VLM."""
import atexit
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import time
import numpy as np
from src.qwen_geometry import render
from src.qwen_rollout import SegmentLedger


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


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
        command = [str(cfg.python_executable), '-u', str(tree/'scripts/qwen_reward_worker.py'),
                   '--model-dir',str(cfg.model_dir), '--prompt',str((tree/cfg.prompt).resolve()),
                   '--output',str(self.output), '--verify',str(int(cfg.verify_first_batch))]
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


class QwenRolloutReward:
    def __init__(self, cfg, envs, H, output):
        self.cfg, self.H = cfg, H
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        (self.output/'samples').mkdir(exist_ok=True)
        self.ledger = SegmentLedger(envs, H, cfg.settlement_interval)
        self.source = getattr(cfg, 'reward_source', 'qwen')
        self.client = QwenClient(cfg, self.output) if self.source == 'qwen' else None
        self.long_sample_saved = False
        self.invalid_sample_reasons = set()

    def collect(self, row, dones, infos):
        self.ledger.collect(row, dones, infos)

    def settle(self, rewards, masks, nav_rewards):
        started = time.perf_counter()
        self.ledger.validate(masks)
        rollout = self.ledger.rollout_id
        snapshots = self.ledger.pending
        tmp = self.output/'tmp'/f'rollout_{rollout:07d}'
        if self.client is not None:
            tmp.mkdir(parents=True, exist_ok=False)
        rows, by_id = [], {}
        render_start = time.perf_counter()
        for s in snapshots:
            if self.client is None or not s['valid_geometry']:
                continue
            stats = s['metadata']
            image = tmp/(s['segment_id']+'.png')
            scene = Path(s['scene_id']).stem
            valid = s['grid'] == 1
            covered = 100*stats['total_valid_cells']/np.count_nonzero(valid)
            new = 100*stats['new_valid_cells']/np.count_nonzero(valid)
            title = f"{scene} / task {s['episode_id']} / E{s['env_id']:02d} | {s['action_count']} actions\nCovered {covered:.1f}% | New {new:.1f}%"
            render(image, s['coords'], s['grid'], s['prior_seen'], s['final_seen'],
                   s['start'], s['end'], s['bounds'], title, 'history', s['mpp'])
            metadata = {k:stats[k] for k in ['action_count','new_area_m2','new_area_m2_per_action',
                                           'prior_seen_area_m2','total_covered_area_m2']}
            rows.append(dict(id=s['segment_id'], image=str(image.resolve()), metadata=metadata,
                             image_sha256=hashlib.sha256(image.read_bytes()).hexdigest()))
            by_id[s['segment_id']] = s
        render_seconds = time.perf_counter()-render_start if self.client is not None else 0.
        response = self.client.score(rollout, rows) if rows else dict(results=[], seconds=0., batches=0)
        nav_before, masks_before = nav_rewards.clone(), masks.clone()
        bonuses = (self.ledger.add(rewards, masks, response['results'], float(self.cfg.beta))
                   if self.client is not None else self.ledger.add_geometry(rewards, masks, float(self.cfg.geometry_alpha)))
        if not nav_before.equal(nav_rewards) or not masks_before.equal(masks):
            raise RuntimeError('Qwen settlement changed navigation rewards or masks')
        qs = [r['q'] for r in response['results']]
        valid_snapshots = [s for s in snapshots if s['valid_geometry']]
        invalid = Counter(s['geometry_reason'] for s in snapshots if not s['valid_geometry'])
        metrics = dict(qwen_bonus_sum=sum(bonuses), qwen_bonus_per_step=sum(bonuses)/(self.H*self.ledger.N),
            qwen_nav_reward_sum=float(nav_rewards[:self.H].sum().item()),
            qwen_mixed_reward_sum=float(rewards[:self.H].sum().item()),
            qwen_segments=len(snapshots), qwen_valid_segments=len(valid_snapshots),
            qwen_valid_fraction=len(valid_snapshots)/len(snapshots),
            qwen_new_area_m2=sum(s['metadata']['new_area_m2'] for s in snapshots if s['valid_geometry']),
            qwen_valid_actions=sum(s['action_count'] for s in snapshots if s['valid_geometry']),
            qwen_geometry_seconds=sum(s['geometry_seconds'] for s in snapshots),
            qwen_render_seconds=render_seconds, qwen_worker_seconds=response['seconds'],
            qwen_total_seconds=time.perf_counter()-started,
            qwen_worker_peak_gpu_gib=response.get('peak_gpu_gib',0.))
        if qs:
            metrics.update(qwen_q_mean=float(np.mean(qs)), qwen_q_min=min(qs), qwen_q_max=max(qs),
                           qwen_q_p10=float(np.quantile(qs,.1)), qwen_q_p90=float(np.quantile(qs,.9)))
            for i in range(5):
                metrics[f'qwen_q_bin_{i}'] = sum(i/5 <= q < (i+1)/5 or (i==4 and q==1) for q in qs)/len(qs)
        for key,count in invalid.items():
            metrics['qwen_invalid_'+key] = count
        if self.source == 'geometry':
            metrics = {key.replace('qwen_', 'geometry_', 1):value for key,value in metrics.items()}
        for name, values in [('segment_length', [s['action_count'] for s in snapshots]), ('bonus', bonuses)]:
            if values:
                for quantile in (0, 50, 90, 100):
                    metrics[f'exploration_{name}_p{quantile}'] = float(np.percentile(values, quantile))
                metrics[f'exploration_{name}_mean'] = float(np.mean(values))
        metrics['exploration_terminal_segments'] = sum(s['terminal'] for s in snapshots)
        metrics['exploration_area_per_valid_action'] = (sum(s['metadata']['new_area_m2'] for s in valid_snapshots) /
            max(1, sum(s['action_count'] for s in valid_snapshots)))
        with (self.output/'segments.jsonl').open('a') as f:
            results = {r['id']:r for r in response['results']}
            for s in snapshots:
                record = {k:s[k] for k in ['segment_id','env_id','reset_index','episode_id','scene_id',
                    'rollout_id','global_start','global_end','start','end','action_count','end_row',
                    'terminal','valid_geometry','geometry_reason']}
                record['reward_source'] = self.source
                if s['valid_geometry']:
                    if self.client is not None:
                        row = next(r for r in rows if r['id']==s['segment_id'])
                        record.update(metadata=row['metadata'], image_sha256=row['image_sha256'],
                                      result=results[s['segment_id']],
                                      bonus=float(self.cfg.beta)*(s['action_count']/self.H)*results[s['segment_id']]['q'])
                    else:
                        record.update(metadata=s['metadata'], geometry_alpha=float(self.cfg.geometry_alpha),
                                      bonus=float(self.cfg.geometry_alpha)*s['metadata']['new_area_m2']/self.H)
                f.write(json.dumps(record,allow_nan=False)+'\n')
        chosen = []
        if rows and rollout % int(self.cfg.sample_interval) == 0:
            chosen += sorted(rows, key=lambda r:by_id[r['id']]['start'], reverse=True)[:2]
        long = [r for r in rows if by_id[r['id']]['start']>=256]
        if long and not self.long_sample_saved:
            chosen += long[:1]; self.long_sample_saved = True
        for row in {r['id']:r for r in chosen}.values():
            s = by_id[row['id']]; prefix=self.output/'samples'/s['segment_id']
            shutil.copyfile(row['image'],str(prefix)+'.png')
            np.savez_compressed(str(prefix)+'.npz', grid=s['grid'], prior_seen=s['prior_seen'],
                final_seen=s['final_seen'], coords=s['coords'], positions=s['positions'],
                headings=s['headings'], start=s['start'], end=s['end'], mpp=s['mpp'])
            write_json(str(prefix)+'.json',dict(row=row,identity={k:s[k] for k in
                ['env_id','reset_index','episode_id','scene_id','rollout_id','start','end','global_start','global_end']},
                result=next(r for r in response['results'] if r['id']==row['id'])))
        with (self.output/'rollouts.jsonl').open('a') as f:
            f.write(json.dumps(dict(rollout_id=rollout,metrics=metrics,invalid_reasons=invalid,
                                   nav_rewards_unchanged=True,masks_unchanged=True),allow_nan=False)+'\n')
        if self.client is not None:
            shutil.rmtree(tmp)  # Only this request's transient rendered PNGs.
        self.ledger.advance()
        return metrics
