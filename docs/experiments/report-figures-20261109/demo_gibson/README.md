# Public SIGN — Gibson ImageNav demonstration

[Download the 720p MP4](public_sign_cantwell1703_720p.mp4) · [Goal](goal.png) · [Start](start.png) · [Midpoint, step 162](midpoint.png) · [Terminal, step 325](terminal.png) · [Summary](summary.json)

One fresh local rollout of **Public SIGN in Cantwell, episode 1703**, recorded on 2026-11-09. It again **succeeded with native STOP at step 325**, SPL **0.1135531493**, actual path length **49.929080 m**. Every recorded pose and action matches the earlier paired experiment. Only this episode/policy was run; no training, scene download, Qwen, recovery, seed changes, threshold changes, or full benchmark.

## Use in the defence PPT

Replace the Habitat-GS video on the navigation-demonstration slide with `public_sign_cantwell1703_720p.mp4` and change its caption to:

> Public SIGN checkpoint · Gibson / Cantwell · Episode 1703 · 10× playback

The deck itself has not been edited. The video is 1280×720, 16:9, H.264/yuv420p, 30 fps, **35.5 seconds**, **3,401,736 bytes**, no audio. The first 32.5 seconds show navigation at **10× simulation time**; the final 3 seconds hold the actual successful STOP observation. The goal image stays fixed, while the main panel shows the current RGB and step. White background with NUS blue/orange.

All **326 actual observations, steps 0–325**, are shown in order. Steps 0–324 each appear for three encoded frames; terminal step 325 appears for 90 frames. No sparse-frame reconstruction or temporal interpolation. Spatial bilinear enlargement is only for presentation: actor input remains 128×128. The black/missing surfaces and blur are from the simulator scene and its original low-resolution observations, without generative alteration.

## Evidence

- `rgb_all_steps.npz`: lossless archive of every RGB observation (`rgb`: 326×128×128×3 uint8; `step`: 0–325), approximately 13 MB.
- `rgb_manifest.csv`: per-step RGB pixel SHA256, STOP and episode-over flags.
- `steps.csv`: every step's actual position, quaternion, policy action, clipped/scaled continuous command, success/SPL, path length and coverage diagnostics. Step 0 has no preceding action.
- `video_frame_mapping.csv`: exact mapping from source step to encoded frame range and timestamps.
- `summary.json`: environment versions, checkpoint SHA256, matched episode/start/goal checks, previous-trajectory comparison, raw RGB archive and video SHA256.
- `recording/`: native config, loader audit, source summary, original sparse keyframe outputs, map and CSV produced by the reused recorder. Dense RGB is in the archive above.
- `preview_000.png`, `preview_162.png`, `preview_325.png`: exact pre-encode presentation frames.
- `video_validation.json`: full-file FFmpeg decode succeeded with no errors; ffprobe decoded all **1,065 frames**, confirming H.264, 1280×720, yuv420p, 30 fps and 35.5 seconds.

Public checkpoint SHA256: `03fa71b514c8ee2fa272d6276499d51313a43b7d71bb31181c0150cc7c050d1a`.

Safety checkpoint SHA256: `b84d291e84216defb730d07d03cb6f25e3555ae447eb1e69057f3427b3c7ec31`.

Environment: Python 3.8.20, Habitat-Sim 0.2.2, Habitat-Lab `1f7cfbdd3debc825f1f2fd4b9e1a8d6d4bc9bfc7`, PyTorch 2.0.1+cu117, RTX 4060 Laptop GPU. The existing sibling `.env-sign` environment and local Cantwell assets were reused. No weights or meshes are duplicated in this directory.

## Reproduce

The only change to `../coverage_comparison/record_pair.py` adds an optional callback after each pose snapshot, including after the terminal action and before any reset. The callback receives copied RGB and row data. With no callback, the old recorder behaves as before; policy, environment, actions, RNG and success logic are unchanged.

From the SIGN root, in the existing environment, choose a **new output directory**:

```bash
DEMO=docs/experiments/report-figures-20261109/demo_gibson
PYTHONHASHSEED=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
python "$DEMO/record_demo.py" --out results/demo_gibson_new
python "$DEMO/export_video.py" --source results/demo_gibson_new
```

To regenerate only the video without inference, run `export_video.py --source "$DEMO"`. The encoder uses stored observations and metadata, and performs complete decode validation. Recording does not auto-reset at termination. The selected task remains `../coverage_comparison/episodes/Cantwell_1703.json.gz`, seed 100, hash seed 0, maximum 500 steps, deterministic native continuous actions and STOP rules.
