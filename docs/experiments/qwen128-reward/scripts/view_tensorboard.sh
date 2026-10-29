#!/bin/bash
set -euo pipefail
exec /scratch/e1538633/liuyi/envs/sign-baseline/bin/python -m tensorboard.main \
  --logdir /scratch/e1538633/liuyi/SIGN-qwen128-reward/results/qwen128_reward_20261029/train_personal_8env/tb \
  --host 127.0.0.1 --port "${QWEN_TENSORBOARD_PORT:-6007}" --load_fast=false --reload_interval 5
