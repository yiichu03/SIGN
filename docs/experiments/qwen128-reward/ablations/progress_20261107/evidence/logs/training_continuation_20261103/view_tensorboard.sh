#!/bin/bash
set -euo pipefail
export CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
exec /scratch/e1538633/liuyi/envs/sign-baseline/bin/python /scratch/e1538633/liuyi/logs/training_continuation_20261103/view_tensorboard.py
