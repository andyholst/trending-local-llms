# A dimension is not "missing" where it cannot apply

**Issue:** [#469](https://github.com/andyholst/trending-local-llms/issues/469)
**Capability:** `data-gap-analysis`

## Why

Every dimension in `DIMENSIONS` was counted against EVERY model. `storage_offload` — a storage
requirement, whose own `why` says "MoE engines (Strata) run big models by streaming experts
from storage" — was therefore reported missing for a dense 2B row that has no expert to stream
and no reason to page weights.

Measured on the store (93 models, `make data-gaps`, 2026-10-25): `storage_offload` was reported
missing on **37** models. Only **23** of those can have one at all; **58** models (a dense 2B, a
27B dense, every small GGUF row) cannot. The inflated count also inflated the dimension's
**rank impact**, which decides what the gap issue leads with.

## What Changes

- **`scripts/data_gap_analysis.py`** — a dimension may carry an `applies` predicate.
  `storage_offload` carries `_applies_storage_offload`: MoE (`35B-A3B`, or the word), a model of
  30B or more, or a measurement on a streaming engine (Strata). `analyse()` splits the result
  into `missing` (applicable, no value) and **`not_applicable`** (the dimension cannot apply),
  the free-text scan skips non-applicable models, and `render()` names the non-applicable set so
  a reader can see it was considered and excluded rather than forgotten.
- **The signature counts only real gaps.** `missing` carries a key with an EMPTY list once every
  model states it; naming that key kept a fully captured dimension in the signature for ever
  (the #472 class, on the other side).
- **`tests/test_data_gap_analysis.py`** — a dense 2B is not missing, an MoE / 70B / Strata model
  is, the dimension stops being a gap once every APPLICABLE model states it, the render names
  the excluded models, and an empty list never reaches the signature.

## Impact

The report and the issue body (truer counts, a new "cannot apply" section). The gap set does not
change: `storage_offload` is still missing on 23 applicable models, so the signature and the
baseline are untouched and no issue is re-filed.

## Not covered (out of scope)

- Other dimensions may deserve a predicate too (`system_ram_min` on a CUDA-only row measured on a
  datacenter card). Filed as a finding rather than guessed at here — the predicate is a claim
  about physics, and each one needs its own evidence.
