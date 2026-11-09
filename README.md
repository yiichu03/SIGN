本分支为 `phase2/qwen-intervention-memory`，最新资料更新于2026-11-09。

- [本地可下载的 checkpoint 与运行命令](ckpt/README.md)：公开 SIGN / safety 已在仓库，新增 Coverage256 125.952M（SR87.57%），附 SHA256 与 CPU 校验。

- [报告/PPT配图第一版：训练曲线、两例500步失败与E2恢复](docs/experiments/report-figures-20261109/README.md)，含PNG/PDF与原始CSV。
- [P1–P4短时视觉历史介入实验](docs/experiments/qwen-intervention-memory/README.md)：实现、配置和138项CPU测试已完成；PBS连接失败，GPU短测和正式验证等待提交。
- [E1–E6完整4200验证结果](docs/experiments/qwen-six-ablation/README.md)：六组均完成；含SR/SPL、Qwen选择、配对救回/误伤及动作前缀证据。
- [当前工作区状态与索引](docs/experiments/qwen-intervention-memory/workspace/STATUS.md)。


## [Project Website](https://nus-core.github.io/assets/standalone/SIGN/index.html)
[![arXiv](https://img.shields.io/badge/arXiv-2310.07473-b31b1b.svg)](https://arxiv.org/pdf/2508.12394)
[![Watch Demo](https://img.shields.io/badge/Watch-Demo-red?logo=youtube&logoColor=white)](https://nus-core.github.io/assets/standalone/SIGN/index.html)

## 1. Install
### 1.1 Install habitat-lab 
```bash
cd SIGN/

# create conda env
conda create -n sign python=3.8
conda activate sign

# install habitat-sim
conda install habitat-sim=0.2.2 withbullet headless -c conda-forge -c aihabitat

# install pytorch
pip3 install torch torchvision torchaudio

# clone habitat-lab code
git clone https://github.com/facebookresearch/habitat-lab.git
cd habitat-lab
git checkout 1f7cfbdd3debc825f1f2fd4b9e1a8d6d4bc9bfc7
pip install -e habitat-lab 
pip install -e habitat-baselines
```
### 1.2 Install other requirements
```bash
cd ..
pip install -r requirements.txt
```

## 2. Download Dataset
Dataset preparation refers to https://github.com/XinyuSun/FGPrompt

<pre>
data
├── datasets
│   └── imagenav
│       ├── gibson
│       │   ├── v1
│       │       ├── train
│       │       └── val
│       ├── hm3d
│       │   ├── v1
│       │       ├── val_easy
│       │       ├── val_hard
│       │       └── val_medium
│       └── mp3d
│           ├── v1
│               ├── test_easy
│               ├── test_hard
│               └── test_medium
└── scene_datasets
    ├── gibson
    │   ├── xx.glb
    │   └── xx.navmesh
    ├── hm3d
    │   ├── scene_id
    │       ├── xx.glb
    │       └── xx.navmesh
    └── mp3d
        ├── scene_id
            ├── xx.glb
            └── xx.navmesh


</pre>

## 3. Run ImageNav Training
```bash
python run_sim.py --overwrite \
--exp-config exp_config/ppo_imagenav_gibson.yaml,policy,reward,sensors \
--run-type train --model-dir results/imagenav/training_log
```

## 4. Run Evaluation
```bash
python run_sim.py \
--exp-config exp_config/ppo_imagenav_gibson.yaml,policy,reward,sensors,eval \
--run-type eval --model-dir ckpt \
habitat_baselines.eval_ckpt_path_dir ckpt/nav_model.pth
```

## 5. Cross-domain Evaluation
difficulty= [val_easy, val_hard, val_medium]
```bash
python run_sim.py \
--exp-config exp_config/ppo_imagenav_hm3d.yaml,policy,reward,sensors,eval \
--run-type eval --model-dir ckpt \
habitat_baselines.eval_ckpt_path_dir ckpt/nav_model.pth \
habitat_baselines.eval.split val_easy
```
difficulty= [test_easy, test_hard, test_medium]
```bash
python run_sim.py \
--exp-config exp_config/ppo_imagenav_mp3d.yaml,policy,reward,sensors,eval \
--run-type eval --model-dir ckpt \
habitat_baselines.eval_ckpt_path_dir ckpt/nav_model.pth \
habitat_baselines.eval.split test_easy
```

## 6. Citation
```
@article{yan2025sign,
  title={SIGN: Safety-Aware Image-Goal Navigation for Autonomous Drones via Reinforcement Learning},
  author={Yan, Zichen and Huang, Rui and He, Lei and Guo, Shao and Zhao, Lin},
  journal={IEEE Robotics and Automation Letters},
  volume={11},
  number={2},
  pages={1962--1969},
  year={2025},
  publisher={IEEE}
}
```


## Frozen-encoder rollout-coverage experiment

[Results, matched-step Gibson evaluation, training curves and reproduction](docs/experiments/frozen-rollout-coverage/README.md).

## Qwen independent top-down scoring

[Experiment overview, images, probabilities and reproduction](docs/experiments/qwen-topdown/README.md) · [9B/2B same-image comparison](docs/experiments/qwen-topdown/reports/pilot_9b_2b.md) · [2B diverse Gibson scenes/tasks](docs/experiments/qwen-topdown/reports/diverse_2b.md)

## Qwen history-window offline evaluation

[Results, controls and validation](docs/experiments/qwen-history-window/VALIDATION.md) · [128/256 report](docs/experiments/qwen-history-window/REPORT.md) · [Blank human review table](docs/experiments/qwen-history-window/human_review.csv)

## Qwen history with solid paths

[Results, controls and validation](docs/experiments/qwen-history-solid/VALIDATION.md) · [128/256 report](docs/experiments/qwen-history-solid/REPORT.md) · [Blank human review table](docs/experiments/qwen-history-solid/human_review.csv)

## Qwen2B inference recovery

[Current results, limitations and discussion](docs/experiments/inference-recovery/iteration_20261108/README.md) · [Branches and worktrees](docs/experiments/inference-recovery/iteration_20261108/BRANCHES.md) · [Protocol and development history](docs/experiments/inference-recovery/ITERATION_PLAN.md)
