# Proposal: alias-identity-gate

Issue: #1207
PR: #1215

## Why

The attribution exception (`measurement_model_aliases`, issue #652) lets a measurement
naming the counterpart's model land on a row. Measured in the shipped store (issue #1207,
2026-11-21): 12 CROSS-IDENTITY pairs — a counterpart whose declared `params` size differs
from the row's (reciprocal qwen3.8-flash-next-125b↔qwen3.8-27b 125B-vs-27B, qwen3.5-0.8b on
the 27B row, lfm2.5-24b↔qwen3.6-35b, qwen3.5-4b↔9b, …). A different-size counterpart
attributes one model's t/s to another through the exception path, bypassing the
misattribution refusal — the trending list's speed figures stop tracing to the model that
produced them. The alias map gate (#652) checked only that a counterpart EXISTS, never that
it shares the row's identity.

## What Changes

- `scripts/update_trending.py`: `params_identity` (reads the STORE `params` field — name
  parsing fails open on variant names), `cross_identity_alias_reason` (ONE implementation,
  rule 6d), the ingest `merge_measurement_aliases(existing, incoming, store)` REFUSES a new
  cross-identity counterpart, and `misattributed_measurement_reason` treats a non-pending
  cross-identity alias as INERT. `CROSS_IDENTITY_ALIAS_PENDING_RULING` + `alias_pending_ruling`
  hold the one documented load-bearing pair (the yume_arasaki bake-off, owner ruling #1210)
  so its shipped measurements stay justified until ruled.
- `scripts/validate.py`: `check_measurement_alias_map` REPORTS the shipped store's
  cross-identity pairs (the #650/#458/#459 report-only precedent — never red every PR for
  history an agent cannot repair); the DANGLING-counterpart hard fail is unchanged.
- `data/models.json`: remove the three non-load-bearing contaminants (qwen3.5-0.8b on the
  27B row; cyber-frost-3.8-mlx and qwopus3.6-35b-a3b-coder-mtp on the 125B row); record the
  official params breakdown on the flash-next row (125B MoE + 51B n-gram + 4B MTP = ~180B
  tensors, live HF card read 2026-11-21 — the "125B" naming is correct, NOT 127B).
- `README.md` re-rendered from the corrected store (`--render-only`).
- `tests/test_alias_identity_gate.py`: 23 checks (parsing, refusal, inertness, ingest
  back-compat, report-vs-dangling, the cleaned shipped store, wiring).

## Impact

- Affected specs: `measurement-attribution` (ADDED: an alias counterpart shares the row's
  params identity; new cross-identity aliases refused at ingest; shipped history reported).
- Affected code: scripts/update_trending.py, scripts/validate.py, data/models.json,
  README.md, tests/test_alias_identity_gate.py.
- Owner rulings tracked separately: #1210 (the flash-next↔27b yume_arasaki pair) and #1213
  (the full 12-pair review — migrate load-bearing justifications to CROSS_MODEL_ALLOW_LIST
  with post evidence or correct the attribution). This change does NOT remove any shipped
  measurement (rule 3b).