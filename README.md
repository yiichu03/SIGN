## 当前研究：Qwen 辅助评估 ImageNav 重复搜索

服务器统一从 `/scratch/e1538633/liuyi` 启动。先读根目录 `AGENTS.md`（工作规则）和 `STATUS.md`（当前进度），操作与复现见 `RUNBOOK.md`，带时间戳的操作／错误／debug 历史见 `WORKLOG.md`。本目录是实际 SIGN 运行仓库；项目命令仍从这里运行。

本地目录与 Git 关系、HM3D v0.2 环境、采集和发布方法统一维护在根目录手册。旧详细研究记录全文已导入根日志的 `MIGRATION-BASELINE` 条目；研究资料包保留发布时的历史说明。

研究资料一键同步：`bash scripts/sync_research_github.sh`；追加 `--check-only` 检查和预览。SIGN 的 origin 为 `yiichu03/SIGN`，研究资料仍发布到 SIGN-SRU 的研究分支；四份根文档在成功发布时保存为资料包的 workspace 副本。

[GitHub 研究资料入口](https://github.com/yiichu03/SIGN-SRU/blob/docs/qwen-reward-review-20261013/docs/research/qwen_relative_diagnostic_2026-10-13/README.md)。下面保留原项目安装与使用说明。

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
