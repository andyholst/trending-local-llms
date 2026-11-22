# Proposal: engine-min-est-visibility-1129

Issue: #1129

## Why

The shipped `gemma-4-e4b` `engine_min_version` value
`SonicBoom 0.0.3 (C++/CUDA, MLIR compiler, zero Python) (est)` records a toolchain
compound — an implementation language, not a build, per #1020 — as a build claim.
The 2026-11-20 measurement on #1129 showed it is invisible in BOTH report classes:
`make data-gaps` names only MISSING values, and the #789 source-post readback class
counts declared estimates without naming them. A stored value no detector will ever
re-claim is a candidate for a human rule-3b decision (rule 3b is additive-only; no
automated deletion), but a human cannot decide what no report surfaces. The planner's
2026-11-21 refinement makes the acceptance criterion checkable: a guard or a report
that actually reads `engine_min_version`.

## What Changes

- `scripts/validate.py` gains `model_level_declared_engine_estimates(store)`, returning
  `(model id, stored value)` for every model-level `engine_min_version` carrying the
  canonical `(est)` marker (rule 2).
- The existing report-only `check_model_footprint_copy` (data stage) NAMES each such
  value — model id, field, stored value — as a rule-3b human-decision candidate.
  Report-only: no new gate failure, no data change, and NO rule-3b decision made here.
- `tests/test_model_footprint_copy.py` gains a regression scenario that is red on the
  pre-change `validate.py`.

## Impact

- `scripts/validate.py` — one helper plus one report block inside an already-wired check;
  no new make target, stage, script or workflow (rule 6d). AGENTS.md §8 already carries
  the guard row for this module (issue #934), so no rulebook row is added.
- `tests/test_model_footprint_copy.py` — one scenario; the existing §8 row covers it.
- No data or contract change (rule 3b: additive only), no AGENTS.md rule change.

## Not covered

- The human rule-3b decision whether each value stays as declared data or is corrected —
  a human act, expressly not made by this change.
- Measurement-side (rather than model-level) declared-estimate engine builds; recorded as
  a separate finding.
- Acquisition of real posts for the `context_tokens`/`engine_min_version` gaps in #1126
  — needs `FIRECRAWL_API_KEY`/`HF_TOKEN`, unavailable in this environment.
