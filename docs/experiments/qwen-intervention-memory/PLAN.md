# Four frozen inference experiments P1–P4

Authorized 2026-11-09 before the project presentation. No PPO training. Base
3f7d445 (runtime behavior e9396ac); the old runtime, jobs and results stay fixed.

All arms use Coverage256 125,952,000 steps / original ckpt.245, SHA256
988c9ecc5b0c704e9a4780f636739aec17cbd323d613f0fbdde4699296886c2c,
the original 4200 Gibson val tasks, 6 environments, seed100/hash0/max500.
Keep window16, yaw-compensated detector and its thresholds, physical scan24,
turn90 degrees, forward8, cooldown64, at most two opportunities/episode,
and at most76 overridden physical actions. Every physical action counts500.
Original SIGN STOP has priority; masks/GRU/actual previous actions are unchanged.

|Arm|Decision before scan|Decision after scan|
|---|---|---|
|P1|Original detector|Always LEFT; no Qwen worker|
|P2|Original detector|Always KEEP; no Qwen worker|
|P3|Qwen current RGB plus last16 executed actions|Original matched rule, first LEFT then RIGHT|
|P4|Same Qwen prompt/actions plus RGB at t-16,t-11,t-5,t|Same matched rule|

P3/P4: the original detector creates a candidate. FP32 Qwen3.5-2B returns
real token softmax over progress/blocked/unknown, T=1. Only progress vetoes
the scan; blocked/unknown preserve the original recovery. Original candidate
mass floor0.1 and tie tolerance1e-6 are integrity/abstention handling, not a
tuned confidence cutoff. Invalid images or model evidence preserve the rule
and are logged; technical errors invalidate a formal run. ID/SHA mismatches
raise. Both a veto and an accepted recovery consume one of the two opportunities.
A veto returns the current SIGN action and sets cooldown64; an accepted scan
uses the existing recovery cooldown unchanged. Opportunity number determines
the rule direction even if the first opportunity was vetoed. No extra calls
after budget exhaustion; disabled/off never starts the worker.

History is the existing bounded full-RGB/action buffer, cleared only by real
episode reset. No new map, retriever, GT state, learned encoder or controller.
P3 and P4 receive identical action metadata; only historical RGB availability
differs. No detector scores or target image are added to this local gate.
P4 also computes an unexecuted current-only shadow response at the exact same
state, on the same resident model. Shadow never controls actions. Record the
extra cost separately; it is audit overhead, not free inference.

Freeze prompt/config before GPU observations. Unit tests cover timing, resets,
STOP, actual actions/masks, no-worker controls, invalid evidence, IDs, budgets,
and exact disabled/regression behavior. Real GPU smoke uses the established
12 engineering tasks, not the old61 for tuning. Check raw token positions,
padding, solo/batch, image order and fixed visual perturbation probes. Probes
describe evidence sensitivity, without fabricated human labels or a positive
SR selection gate. No iterative tuning to make pilot success positive.

Formal P1–P4 launch only after technical checks pass, independent outputs,
source manifests and immutable runtime checkout, one A40/36CPU/240GB/6h each,
autox routed to batch_gpux respecting four concurrent jobs. Report paired
SR/SPL rescue/harm against existing off/A/rule and P3/P4; distinguish gate
choice changes, actual first-command changes, same-prefix evidence and costs.
Existing 4200 is a repeatedly used validation benchmark, not a fresh held-out set.
