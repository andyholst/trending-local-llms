# Proposal: attribution-joint-figure-alias

Issue: #650 — "Ranked dimensions are gaps in what we CAPTURE, not in what people
report" (the measurement-attribution half; this change lands the documented-exception
half. The removal half is a rule-3b human decision, reported on the issue.)

## Why

The attribution scan (`make validate`, `data` stage, report-only) flags two shipped
measurements whose text names a DIFFERENT model than the row they sit on:

1. `qwen3.6-35b-a3b` / vLLM 309 t/s — the post (witcheer, 2026-07-20) is a JOINT
   benchmark: "Qwen3.8-27B … vs Qwen3.6-35B … on the same 3090", 309 vs 292. The
   figure genuinely belongs to the 35B MoE row (Humming vs Marlin kernels on it),
   and the sentence names the comparison model `Qwen3.8-27B`, so the scan's
   joint-figure rule reports the row. The mechanism #652 built for exactly this
   case is the row's `measurement_model_aliases` data key — the exception belongs
   on the DATA, not in code — and no shipped row carried it.
2. `qwen-3.6-27b` / llama.cpp 140 t/s — the post (0xbelorix, 2026-07-10) measured
   "qwen 3.5 35b" through LM Studio: a genuine misattribution, not an exception.
   Removing a shipped measurement is a rule-3b human decision; this change does
   NOT remove it. It stays reported until the owner rules on issue #650.

## What Changes

- `data/models.json`: the `qwen3.6-35b-a3b` row gains
  `"measurement_model_aliases": ["qwen3.8-27b"]` — the contract-declared optional
  key (rule 3b additive; the counterpart is a model id in the store, so
  `check_measurement_alias_map` resolves it).
- `tests/test_measurement_attribution.py` gains
  `test_the_shipped_joint_figure_is_documented_as_data`: the shipped 35B-A3B row
  carries the exception, the joint figure is no longer an attribution WARN, the
  owner-undecided `qwen-3.6-27b` hit is STILL reported, and the shipped alias
  passes the counterpart gate.

## Impact

- `make validate`'s attribution WARN list over the shipped store drops from two
  entries to the one the owner has not yet ruled on.
- No ingest, README, contract or workflow behaviour changes.

## Not covered

- Removal (or replacement) of the misattributed `qwen-3.6-27b` llama.cpp 140 t/s
  measurement — rule 3b requires an explicit human decision; the evidence and the
  request live on issue #650.
- The report-only weight-gb contradiction on `bonsai-2-9b` surfaced by the same
  scan run — a separate finding (#615's class).
