"""Explicit checkpoint continuation; episode/simulator state is always reset."""
import hashlib
import json
import math
from pathlib import Path

import torch


def restore_training(trainer):
    cfg = getattr(trainer.config, 'training_continuation', None)
    if cfg is None or not cfg.checkpoint:
        return
    path = Path(cfg.checkpoint)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != cfg.sha256:
        raise RuntimeError('Continuation checkpoint SHA mismatch')
    checkpoint = torch.load(str(path), map_location='cpu')
    state = checkpoint['state_dict']
    current = trainer.agent.state_dict()
    if set(state) != set(current) or any(state[k].shape != current[k].shape or state[k].dtype != current[k].dtype for k in current):
        raise RuntimeError('Continuation model keys, shapes or dtypes mismatch')
    if not all(torch.isfinite(value).all().item() for value in state.values()):
        raise RuntimeError('Non-finite continuation model')
    step = checkpoint.get('extra_state', {}).get('step')
    batch = trainer.config.habitat_baselines.num_environments * trainer.config.habitat_baselines.rl.ppo.num_steps
    total = trainer.config.habitat_baselines.total_num_steps
    previous_walltime = float(checkpoint.get('extra_state', {}).get('wall_time', 0.))
    if type(step) is not int or not 0 < step < total or step % batch:
        raise RuntimeError('Invalid cumulative continuation step')
    if not math.isfinite(previous_walltime) or previous_walltime < 0:
        raise RuntimeError('Invalid previous wall time')
    learner = checkpoint.get('learner_state')
    if learner is None and not cfg.allow_legacy_weights:
        raise RuntimeError('Checkpoint has no optimizer state; explicit legacy opt-in required')
    if learner is not None and learner['num_updates_done'] != step // batch:
        raise RuntimeError('Optimizer checkpoint counter mismatch')
    prefix = 'actor_critic.net.visual_encoder.'
    encoder = [k for k in current if k.startswith(prefix)]
    if not encoder or any(not torch.equal(current[k].cpu(), state[k]) for k in encoder):
        raise RuntimeError('Checkpoint changes the frozen public encoder')
    visual = trainer.actor_critic.net.visual_encoder
    if visual.training or any(p.requires_grad for p in visual.parameters()):
        raise RuntimeError('Visual encoder is not frozen')
    trainer.agent.load_state_dict(state, strict=True)
    if learner is not None:
        trainer.agent.optimizer.load_state_dict(learner['optimizer'])
        trainer.actor_critic.Qc_opt.load_state_dict(learner['qc_optimizer'])
    trainer.num_steps_done = step
    trainer.num_updates_done = step // batch
    trainer._last_checkpoint_percent = trainer.percent_done()
    trainer._continuation_previous_walltime = previous_walltime
    trainer._continuation_start_step = step
    trainer.agent.use_aug_flag = step < int(trainer.config.habitat_baselines.rl.data_augmentation.stop_step)
    loaded = trainer.agent.state_dict()
    if any(not torch.equal(loaded[k].cpu(), state[k]) for k in state):
        raise RuntimeError('Checkpoint model was not restored exactly')
    output = Path(trainer.config.habitat_baselines.checkpoint_folder).parent
    receipt = dict(checkpoint=str(path), checkpoint_sha256=digest, cumulative_start_step=step,
        cumulative_start_update=trainer.num_updates_done, previous_walltime=previous_walltime,
        mode='learner_state' if learner is not None else 'legacy_weights_optimizer_reset',
        model_states_restored=len(state), encoder_items_unchanged=len(encoder),
        episodes_and_recurrent_state_reset=True, coverage_history_reset_with_new_episodes=True,
        rng_reseeded=True, exact_trajectory_resume=False, mrq_update_active=trainer.agent.use_aug_flag,
        qwen_local_rollout_offset=step // batch,
        initial_parameter_hashes={k:hashlib.sha256(v.cpu().numpy().tobytes()).hexdigest() for k,v in loaded.items()})
    (output / 'continuation.json').write_text(json.dumps(receipt, indent=2, allow_nan=False)+'\n')


def continuation_pending(trainer):
    cfg = getattr(trainer.config, 'training_continuation', None)
    limit = int(getattr(cfg, 'stop_after_steps', 0))
    return limit <= 0 or trainer.num_steps_done - trainer._continuation_start_step < limit


def add_learner_state(trainer, checkpoint):
    cfg = getattr(trainer.config, 'training_continuation', None)
    if cfg is not None and cfg.checkpoint:
        checkpoint['learner_state'] = dict(version=1,
            num_updates_done=trainer.num_updates_done,
            optimizer=trainer.agent.optimizer.state_dict(),
            qc_optimizer=trainer.actor_critic.Qc_opt.state_dict(),
            simulator_and_rng_state_saved=False)
