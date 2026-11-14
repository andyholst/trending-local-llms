# Proposal: footprint-readback-store-gate-788

Issue: #788 — "Stored footprint values their captured source posts nowhere state are surfaced but never repaired".
PR: #933

## Why

Issue #531 added `check_source_post_readback` (report-only) and it flagged **23** shipped-store
footprint values whose cited post states neither the stored value in its fields nor in its text
(`weight_gb`, `context_tokens`, `system_ram_min`, `storage_offload`, `engine_min_version`).
That residue is still 23 on `origin/master` — the scan is report-only, nothing reads its count,
so every merge since #531 left the rows exactly as flagged while the card-fit tables publish
them as measured advice.

But nothing LOCKS that state. The scan is report-only by design (a parser miss must not red a
refresh), and `tests/test_source_post_readback.py` asserts only against temp fixtures. A merged
edit can reintroduce a bad footprint value — `bonsai-2-27b`'s `5.93GB` vs the captures' `5.95GB`
was exactly such a drift — and every gate would stay green while the card-fit tables publish it
as measured advice. The issue's Done-when names the residue gate: the flag count must STAY a
near-zero, individually-attributable residue.

## What Changes

- **Data reconciliation (the 23 flagged values → 0 flags):**
  - **5 values corrected** to the figure the cited capture states (`30720`→`131072`,
    `90K`→`110K`, `262000`→`131072`, `ternary PQ2_0`→`ternary PQ2_0 7.21GB`,
    `official checkpoint`→`official checkpoints`) — rule 3b: these keys only GAIN accuracy,
    no t/s or counter is touched, every edit names its capture's own phrase.
  - **17 values carry the canonical `(est)` marker** (rule 2's own notation) — estimates that
    are individually attributable on their row instead of silent contradictions.
  - **1 flag was a scan imprecision**: `llama.cpp with MTP=2` was flagged only because the
    capture's own structured `engine_min_version: "MTP=2"` was matched one-way.
- **Scan precision (`scripts/validate.py`)**: structured captures confirm both ways for the
  SAME field (free text stays one-way); annotation brackets are stripped in the confirmation
  norm; an `(est)`-marked footprint value is treated as a declared estimate (never a
  contradiction flag) and counted by `source_post_declared_estimates` so the report shows the
  visible residue instead of hiding it.
- **`tests/test_source_post_readback.py`** gains shipped-store + precision tests:
  - `test_the_shipped_store_flags_no_unsupported_footprint_values` — runs the REAL
    `source_post_figure_flags` against the REAL `data/models.json` + `data/raw/` and fails with
    per-flag attribution (model, field, stored value, post URL) if any flag appears: the residue
    is pinned at zero, individually attributable, exactly the Done-when wording.
  - `test_the_store_gate_fires_on_a_planted_drift` — plants a `5.93GB`-vs-`5.95GB`-class drift
    into the in-memory copy of the REAL store and proves the gate goes RED on it, so the shipped
    test is a live gate, not a tautology (rule 6m: the real scan runs).
  - `test_a_declared_estimate_is_attributable_not_a_contradiction`,
    `test_the_captures_own_structured_value_supports_a_fuller_distillation`,
    `test_annotation_brackets_do_not_break_confirmation` — the three precision rules above,
    each with its opposite precision case (an unmarked value, a cross-field value, a longer
    stored prose tail stays flagged).
- **AGENTS.md §8** gains the guard row; §4 states the `(est)` convention for footprint rows
  (rule 3c: this issue's AGENTS.md diff is exactly those two sections).

Additive data only: no key removed, no t/s raised or lowered, no counter shrunk, no contract
or stage change (the readback scan stays report-only by design — the gate lives in `make test`).

## Impact

- Data: `data/measurements.json` (22 footprint field values reconciled; t/s untouched),
  `data/models.json` (model-level mirror where the value matched exactly).
- Validator: `scripts/validate.py` — `source_post_figure_flags` precision rules,
  `source_post_declared_estimates`, the report line now names the `(est)` residue.
- Specs: `validate-source-post-readback` gains the shipped-store gate + precision scenarios.
- Tests: `tests/test_source_post_readback.py` (already wired into `make test` via
  `scripts/run_tests.sh`'s file discovery — rule 6d, no new target needed).
- No Makefile, workflow or contract change.

## Not covered

- Making the readback FAIL ingest (issue #888 owns the refusal-trace gap; refusing new
  unsupported footprint values at ingest needs that trace first).
- Re-reconciling already-shipped rows: the flag count is already 0 on `origin/master` — this
  change is the gate that blocks it from drifting back.
