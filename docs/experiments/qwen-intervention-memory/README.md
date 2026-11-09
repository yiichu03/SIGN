# P1–P4: Qwen pre-scan intervention with short visual history

Four inference experiments on the frozen Coverage256 125.952M checkpoint.
No PPO training. The original A, E1–E6, matched rule and ongoing jobs remain
in their immutable worktrees and independent outputs.

| Arm | Before scanning | After the original 24-action scan |
|---|---|---|
| P1 | Original detector | Always LEFT |
| P2 | Original detector | KEEP: immediately return the current SIGN proposal |
| P3 | Qwen, current RGB + last16 actual actions | Original alternating rule |
| P4 | Same prompt/actions, add3 historical RGBs | Original alternating rule |

P3/P4 use the same resident FP32 Qwen3.5-2B worker and true first-token logits
over `progress / blocked / unknown`, T=1. `progress` skips scanning and returns
the current policy action; `blocked` and `unknown` preserve matched-rule
recovery. No extra confidence threshold. Both a skip and recovery consume one
of two opportunities. The short history is the existing 17-observation/16-action
buffer; no GT, map, detector score, target distance, new encoder or retriever.
Images occur at t-16, t-11, t-5 and t. P3 has only the last RGB but identical
executed-action metadata. The goal image remains available to SIGN itself.

P4 saves an additional, unexecuted current-only shadow answer at the exact same
state, exposing whether historical images change the classification and the
intervention decision. Its cost is audit overhead and is included in measured
worker/runtime costs. P1/P2 never initialize a Qwen worker.

## Frozen protocol and implementation

See [preregistered settings](PLAN.md). Original Gibson4200,6env,seed100/hash0,
max500, window16, cooldown64, scan24, turn90°, forward8, at most76 physical
intervention actions. STOP, GRU, real masks and executed-action feedback retain
the existing native evaluator behavior.

- [Shared controller](../../../src/inference_recovery.py): fixed direction and
  pre-scan hook; the existing scan/recovery implementation is reused.
- [History and gate validation](../../../src/recovery_gate.py).
- [Prompt](../../../scripts/prompts/recovery_intervention.txt),
  [minimal defaults](../../../src/config/inference_intervention.yaml),
  [central arm switches](../../../scripts/memory_four_arm.py).
- [Worker](../../../scripts/recovery_worker.py): new role-checked protocol on
  the existing loader/batched real probability readout.
- [Unit tests](../../../tests/test_intervention_memory.py),
  [GPU engineering check](../../../scripts/smoke_intervention.py).

## Reproduction and submission

Commit all runtime files, create a detached runtime worktree, then run:

```bash
python scripts/prepare_intervention.py --output /absolute/new_batch
```

This writes immutable manifests/tasks and prepared commands without submitting.
Execute its `check` command first. Only after `checks/check_summary.json` passes:

```bash
python scripts/submit_intervention.py --batch /absolute/new_batch
```

The submitter verifies source/assets, refuses existing receipts, submits four
independent 1A40/36CPU/240GB/6h autox jobs, and a CPU report dependent on all4.
Never reuse an output folder or change a queued/running source checkout.
Report command: `python scripts/report_intervention.py --batch BATCH --output NEW_DIR`.

Audit includes every gate input/action binding, probability/logit, unknown or
invalid reason, P4 shadow, actual scan/recovery commands, same-task SR/SPL,
paired rescue/harm, first-action differences and prefix support. No model
decision change is inferred from success differences alone. Full4200 is the
existing validation set. Engineering probes do not supply human labels or a
small-set success requirement.

Runtime source is **8a94adf8bfb0c893ff850c6daf0c321cd73a4fcb**, detached worktree
`SIGN-qwen-intervention-runtime-8a94adf`. Batch:
`/scratch/e1538633/liuyi/logs/qwen_intervention_memory_20261109/runtime_8a94adf`.

CPU: **138 tests passed** (132 controller/worker/readout +6 checkpoint), and
7 merged configurations checked. Tokenizer IDs progress13954/blocked59276/unknown15615;
real GPU answer-boundary, padding and batch validation remains pending.

## Current status: 2026-11-09T08:23:49+08:00

The first GPU check submission at 01:58 on November9 failed with PBS
`cannot connect to server`; no job ID was issued. Account lookup and GitHub
connectivity have recovered; PBS still returns `Connection refused / errno15010`.
The authorized one-shot launcher remains alive and waits for scheduler recovery,
then submits the GPU check, and submits P1–P4 only after its technical gate passes.
There is currently no successful check or formal submission receipt, and no
GPU check result. Do not launch another waiter or duplicate these submissions.

[Latest infrastructure snapshot](evidence/infrastructure_20261109_morning.json),
[launcher snapshot](evidence/launch_state_20261109_morning.json),
[initial check attempts](evidence/check_submission_attempts.jsonl),
[launch control SHA](evidence/launch_control_manifest.json),
[CPU tests](evidence/unit_tests.txt), [configuration checks](evidence/config_preflight.json).

E1–E6 now all have complete4200 results and paired action-prefix reports:
[six-arm final results](../qwen-six-ablation/README.md).
E2 has SR88.619048/SPL53.781069%,149 choices:147LEFT/2RIGHT.
Relative to A it rescues8/harms0 (model-prefix-supported7/0);
relative to matched rule4/3 (model-prefix-supported2/2).
This motivates P1's fixed-direction control; P1–P4 have no navigation results yet.

Server-maintained workspace snapshots: [STATUS](workspace/STATUS.md),
[RUNBOOK](workspace/RUNBOOK.md), [WORKLOG](workspace/WORKLOG.md),
[AGENTS](workspace/AGENTS.md). Runtime source stays8a94adf; documentation commits
on this branch may advance without changing the runtime checkout.
