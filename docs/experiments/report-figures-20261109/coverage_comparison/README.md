# Local paired Gibson trajectories — 2026-11-09

Three real episode pairs, recorded on a Linux laptop using SIGN commit `55a2f9e`, Habitat-Sim **0.2.2**, and Coverage256 **125.952M**. No training, Qwen, recovery, or full validation run. The six recorded runs use identical settings within each pair; this is qualitative case evidence, not a new 4,200-episode benchmark or an isolated causal ablation of the reward.

## Recommended PPT figures

1. **[Cantwell / 1703 — paired PNG](Cantwell_1703/paired_comparison.png)** ([PDF](Cantwell_1703/paired_comparison.pdf)): strongest main-slide example. Both agents succeed, but Coverage reaches the goal in 82 rather than 325 steps, with a visibly shorter route. Use beside or after slide 14 of `SIGN_NUS_Defense_English_Updated_v5.pptx`.
2. **[Cantwell / 1688 — paired PNG](Cantwell_1688/paired_comparison.png)** ([PDF](Cantwell_1688/paired_comparison.pdf)): success-versus-timeout example in this local run. Coverage succeeds in 124 steps; Public times out at 500.
3. [Mosquito / 3564 — paired PNG](Mosquito_3564/paired_comparison.png) ([PDF](Mosquito_3564/paired_comparison.pdf)): supplementary limitation; both fail. Not evidence that Coverage always explores more effectively.

Each case also has `rgb_keyframes.png/.pdf`, a shared goal saved under both methods, initial/terminal RGB and a few intermediate frames, `steps.csv`, `summary.json`, `config.yaml`, `load_audit.json`, `map.npz`, and `pair_verification.json`. No scene meshes or duplicate model weights are included in this report directory.

Suggested caption for the main example:

> Paired image-goal navigation in Cantwell (episode 1703). With the same start, heading and goal image, SIGN + Coverage Reward reaches the goal in 82 steps versus 325 for Public SIGN (SPL 0.400 versus 0.114). Recovery is disabled. Shaded regions show observed area; coverage curves stop when each episode ends. This is a selected local example, not an aggregate performance estimate.

## Recorded results

| Episode | Policy | Success | Steps | SPL | Path (m) | New area (m²) |
|---|---|---:|---:|---:|---:|---:|
| Cantwell/1703 | Public SIGN | 1 | 325 | 0.113553 | 49.929 | 25.76 |
| Cantwell/1703 | SIGN + Coverage Reward | 1 | 82 | 0.399662 | 14.186 | 13.85 |
| Cantwell/1688 | Public SIGN | 0 | 500 | 0 | 52.328 | 16.91 |
| Cantwell/1688 | SIGN + Coverage Reward | 1 | 124 | 0.199243 | 19.005 | 16.28 |
| Mosquito/3564 | Public SIGN | 0 | 500 | 0 | 95.637 | 45.74 |
| Mosquito/3564 | SIGN + Coverage Reward | 0 | 500 | 0 | 75.997 | 45.24 |

Coverage total is not an efficiency ranking when episodes end at different times. In Cantwell/1703 the Coverage agent succeeds sooner and therefore does not need to observe as much total area. Curves end at the actual final step and are not extended to 500.

Selection: Mosquito/3564 and Cantwell/1688 were requested historical diagnostic cases. Cantwell/1703 was the third and final pair, chosen from an already recorded public pilot in the same scene to include another navigation task. All three attempted pairs are retained; no additional episode sweep was performed. A native entry-point smoke check re-ran only Coverage/Cantwell1688.

**Do not mix this Cantwell/1688 result with the previous server failure figure.** This fresh local run succeeds; the existing `../failures/Cantwell_1688/` record failed. The local simulator is 0.2.2, matching the repository installation instructions, and the local software/rendering stack is recorded below. The exact cause of the cross-run difference was not established. Same-episode identity across the two local policies is verified, but bitwise reproduction of the old server trajectory is not claimed. The old figure on PPT slide 8 remains a historical example.

## Protocol and loading

- Native config: `exp_config/ppo_imagenav_gibson.yaml,policy,reward,sensors,eval`; `SafeNavNetPolicy`; seed 100, `PYTHONHASHSEED=0`, one environment, 500-step limit, `deterministic=True, eval=False`.
- Actor inputs: current RGB + image goal, both 128×128, same resize/crop and no augmentation. Depth is present as in the native setup. Coverage geometry is used only by the recorder, never fed to the actor or added as evaluation reward.
- Native continuous action: normalized vector order **angular, linear**; angular range −15 to +15 degrees/s, linear range 0–0.25 m/s, 1-second action. STOP uses the original linear/angular thresholds. CSV stores policy outputs, clipped executed inputs, scaled commands, pose/quaternion, cumulative actual 3D path, coverage, success, SPL, and termination flags. Scaled commands on a STOP step are threshold inputs; STOP causes no motion.
- Navigation checkpoints load through the native `trainer.agent.load_state_dict(..., strict=False)`. Coverage contains all 103 expected state keys and all **42 frozen visual encoder tensors match Public SIGN**. It is not loaded as a standalone raw actor state dict and not initialized with a random visual encoder.
- Both policies subsequently load the same `safety_model.pth` Qc tensors, preserving `policy.yaml` and the repository loader. Public's initial missing Qc keys are filled by this safety checkpoint; obsolete Qc/LPIPS checkpoint keys are ignored as in the native loader. **Native simulation `SafeNavNetPolicy.act` does not call the separate `USL_correction` routine**; the recorder does not introduce that additional intervention. Recovery is off in both arms.
- Pair verification checks source episode, start pose/quaternion, initial RGB pixel hash, goal RGB pixel hash, seed, step limit, and safety SHA. Goal pixels remain constant throughout each rollout. Direct single-environment stepping prevents vector auto-reset from replacing terminal RGB.
- Coverage uses native `ObservedCoverage`: 0.1 m grid, 3 m range, 90° XZ fog-of-war proxy. Initial visible cells are excluded from cumulative new area and shown in darker tint. Navigation is evaluated with native success/SPL. Maps share world coordinates, extent and aspect ratio. Multi-height observations are a projected union, not a 3D surface-area measurement.

## Minimal data and environment

The initially empty local Gibson scene directory was populated with **only** `Cantwell.glb`, `Cantwell.navmesh`, `Mosquito.glb`, `Mosquito.navmesh`.

- Public scene source: [Meta Gibson Habitat ZIP](https://dl.fbaipublicfiles.com/habitat/data/scene_datasets/gibson_habitat.zip), 1,468,698,464 bytes as a whole. HTTP Range transferred **43,761,609 bytes** including directory and member headers; four selected compressed members total 43,745,254 bytes. ZIP CRC is verified by Python `zipfile`; per-file SHA256 is in [runtime.json](provenance/runtime.json). No full ZIP downloaded; no API key used.
- Exact project episode source: FGPrompt [dataset archive](https://drive.google.com/file/d/1XNElxwOCUO8BDFO3U1g3wZTzcgjPeCdC/view), specifically `datasets/imagenav/gibson/v1/val/val.json.gz`. Only **507,288 bytes** transferred via Range from its 649,504,436-byte ZIP. Extracted gzip SHA256: `9357815baaf9b9afade99e75ce074ef6f25994a6a428ebde11687f2a08f57aa1`. The three selected one-episode subsets are included under `episodes/`.
- An initially checked [original ImageNav dataset](https://github.com/facebookresearch/image-goal-nav-dataset) uses different IDs; a Hugging Face validation mirror assigns ID 1688 to Eastville. Neither was used for the paired runs. Always match scene and source coordinates, not episode ID alone. The FGPrompt records match both historical starting positions.
- CPU: Intel i9-13900H; RAM 15 GiB; RTX 4060 Laptop 8 GiB; NVIDIA driver 580.178.04; about 898 GiB free on `/home` at setup.
- Independent environment: `A_final/.env-sign`, Python 3.8.20; Habitat-Sim 0.2.2 headless/bullet; Habitat-Lab `1f7cfbdd3debc825f1f2fd4b9e1a8d6d4bc9bfc7`; PyTorch 2.0.1 CUDA 11.7. Existing `habitat` and other environments were not modified. [Conda package lock](provenance/conda-explicit.txt), [pip package list](provenance/pip-freeze.txt), [runtime and SHA record](provenance/runtime.json).

The official [Gibson data page](https://github.com/StanfordVL/GibsonEnv/blob/master/gibson/data/README.md) documents the dataset license. The publicly reachable transport URL does not change the dataset license. Episode dataset provenance/license: [ImageNav dataset](https://github.com/facebookresearch/image-goal-nav-dataset), CC BY-NC 4.0.

## Reproduction

For a fresh machine, [setup_local.sh](setup_local.sh) contains the environment installation commands used here (requires Conda and uv). The package snapshots above record the resolved versions; `pip-freeze.txt` is an audit record with local editable/build paths, not a portable requirements file. The initial missing `ifcfg` and `faster-fifo` imports were resolved by installing those packages; no Habitat or SIGN source patch was needed.

From the SIGN repository root, with the isolated environment active and the four scene files in `data/scene_datasets/gibson/`:

```bash
REPORT=docs/experiments/report-figures-20261109/coverage_comparison
PYTHONHASHSEED=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
python "$REPORT/record_pair.py" \
  --task "$REPORT/episodes/Cantwell_1703.json.gz" \
  --out results/coverage_pair_new/Cantwell_1703
python "$REPORT/plot_pairs.py" results/coverage_pair_new/Cantwell_1703
```

Repeat with the other included task files if desired. Output directories must be new. No full benchmark is necessary.

To obtain just the scene files (destination must not already contain them):

```bash
python "$REPORT/remote_zip_subset.py" \
  https://dl.fbaipublicfiles.com/habitat/data/scene_datasets/gibson_habitat.zip \
  --match Cantwell Mosquito --out data/scene_datasets/gibson
```

The helper refuses a server that ignores Range and has a 2 GB transfer cap. It downloads only selected ZIP members and checks their CRC. `requests` is needed for this helper; plotting uses NumPy, Matplotlib and Pillow without a simulator.

Validation: [validation.json](validation.json) and [validate_results.py](validate_results.py) check episode identity, actual step count, trajectory length, cumulative coverage/mask area, native SPL consistency, goal hashes and terminal frames. The native `run_sim.py` one-episode check reports success=1, SPL=0.1992 for Coverage/Cantwell1688, matching the recorder ([log](provenance/run-native.log)). Figures were visually inspected. This package contains no fabricated trajectory or generated RGB.
