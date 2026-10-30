#!/bin/bash
# Start or reuse the viewer on the same login node as this SSH connection.
set -euo pipefail
export CUDA_VISIBLE_DEVICES=""
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
exec /scratch/e1538633/liuyi/envs/sign-baseline/bin/python \
  /scratch/e1538633/liuyi/logs/gibson_reproduction_20261026/view_personal_tensorboard.py
