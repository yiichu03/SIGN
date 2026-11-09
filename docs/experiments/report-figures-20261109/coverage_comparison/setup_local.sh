#!/usr/bin/env bash
# Execute from SIGN root. Installs only into a new sibling prefix and source tree.
set -euo pipefail
SIGN_PARENT=$(dirname "$PWD")
SIGN_ENV="$SIGN_PARENT/.env-sign"
SIGN_LAB="$SIGN_PARENT/habitat-lab-sign"
test ! -e "$SIGN_ENV" || { echo "Environment already exists: $SIGN_ENV"; exit 1; }
conda create -y -p "$SIGN_ENV" python=3.8 habitat-sim=0.2.2 withbullet headless -c conda-forge -c aihabitat
git clone --filter=blob:none https://github.com/facebookresearch/habitat-lab.git "$SIGN_LAB"
git -C "$SIGN_LAB" checkout 1f7cfbdd3debc825f1f2fd4b9e1a8d6d4bc9bfc7
uv pip install --python "$SIGN_ENV/bin/python" \
  'torch==2.0.1' 'torchvision==0.15.2' 'numpy<1.24' 'setuptools<70' wheel \
  'gym==0.22.0' 'matplotlib==3.5.0' 'opencv-python==4.7.0.72' \
  'protobuf==3.20.1' 'tensorboard==2.8.0' 'moviepy==1.0.3' \
  'einops==0.3.0' 'ruamel.yaml==0.17.4' lpips lmdb 'webdataset==0.1.40' \
  'hydra-core==1.2.0' 'omegaconf==2.2.3' yacs numpy-quaternion \
  'numba<0.58' 'scipy<1.11' imageio imageio-ffmpeg tqdm 'transformers<4.40' \
  ftfy regex ifcfg 'timm==0.6.13' 'scikit-image<0.22' 'scikit-learn<1.4' \
  'psutil<6' faster-fifo
uv pip install --python "$SIGN_ENV/bin/python" --no-deps --no-build-isolation \
  -e "$SIGN_LAB/habitat-lab" -e "$SIGN_LAB/habitat-baselines"
echo "Activate with: conda activate $SIGN_ENV"
