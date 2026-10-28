# Coverage reward settlement interval

This ablation keeps the frozen visual encoder, weight 0.1, eight environments,
256 steps per environment, and all original navigation/PPO settings. It changes
only where the coverage reward is placed in a collected rollout.

`habitat.task.observed_coverage.settlement_interval` controls additional boundaries:

- `0` (default): retain the original episode and rollout boundaries.
- `32`: also settle at rollout steps 32, 64, ..., 256, independently in each environment.

Real episode endings always split segments. Collect the complete rollout before
adding bonuses and calculating returns. Each segment receives
`weight * segment_new_area / rollout_steps` at its last step. The denominator
remains 256, including short segments. The undiscounted total on an identical
trajectory is conserved; discounted returns and credit assignment change.
These additional boundaries neither change terminal masks nor clear coverage
history. Coverage resets only on a real episode reset. Initial views earn no bonus.

Start a fresh training output directory with the same public encoder initialization:

```bash
python run_sim.py \
  --exp-config exp_config/ppo_imagenav_gibson.yaml,policy,reward,sensors,rollout_coverage \
  --run-type train --model-dir results/gibson_coverage_settle32 \
  habitat_baselines.num_environments 8 \
  habitat_baselines.rl.ppo.num_steps 256 \
  habitat_baselines.rl.ddppo.pretrained_encoder True \
  habitat_baselines.rl.ddppo.pretrained_weights ckpt/nav_model.pth \
  habitat_baselines.rl.ddppo.train_encoder False \
  habitat_baselines.num_checkpoints -1 \
  habitat_baselines.checkpoint_interval 250 \
  habitat_baselines.log_interval 10 \
  habitat.task.observed_coverage.settlement_interval 32
```

Use the existing SIGN environment and `PYTHONHASHSEED=0`. The configuration keeps
seed 100 and the 300M environment-step cap. TensorBoard `reward` remains the
environment's navigation reward; `learner/coverage_*` records the added bonus and
area separately. Evaluation continues to use `...,policy,reward,sensors,eval`
without the coverage configuration (six environments, 500-step episodes).

CPU tests in the SIGN environment, from the repository root:

```bash
python -m unittest discover -s tests -p 'test_coverage_settlement.py' -v
```

Tests cover multiple episodes, coincident boundaries, partial rollouts, eight
environments, reward conservation, zero-weight identity, configuration validation,
and propagation of GAE across settlement boundaries. Short training checks verify
execution and numerical validity; they do not establish navigation improvements.
