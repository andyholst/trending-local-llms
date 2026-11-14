# Proposal: footprint-hard-fields-gate-789

Issue: #789 — "The report-only scan cannot become a gate until the prose-field false-positive rate is measured".
PR: #954

## Why

#788 reconciled the 23 readback flags to **0 residue** and pinned that with
`tests/test_source_post_readback.py`'s shipped-store gate — but the *pipeline* scan
`check_source_post_readback` is still report-only for **all five** footprint fields
(`validate.py` registers it as `source-post readback (report only)`), so a new merge can
publish a contradicted `weight_gb` (the figure that drives the card-fit rows) and every
failing gate stays green; only a WARN line mentions it.

The reason the whole scan was report-only was the measured precision problem: of the 23
flags, **10 were `engine_min_version`** prose distillations the captured post does not
restate verbatim (`llama.cpp dev build with PR #27342, --spec-type draft-dflash…`).
Gating on prose reds refresh PRs on parser misses — the exact outcome #458/#459 refused.
The four numeric/hard fields have no such problem: their stored values are figure tokens
(`5.95GB`, `262144`, `110K`, `7.21GB`), and a captured post either states the figure or it
does not. With residue pinned at 0, promoting exactly those fields costs nothing today and
locks the class tomorrow.

## What Changes

- `validate.py` declares the field split ONCE: `_SOURCE_POST_GATE_FIELDS`
  (`weight_gb`, `context_tokens`, `system_ram_min`, `storage_offload`) and
  `_SOURCE_POST_REPORT_FIELDS` (`engine_min_version`); `_SOURCE_POST_FOOTPRINT` remains
  their union (rule 3b — no key removed).
- `check_source_post_readback` fails the `data` stage on every hard-field flag (each named
  with model, engine, tps, field, value and source post) and keeps prose-field flags as a
  WARN report with its reason, so a parser miss on `engine_min_version` cannot red a
  refresh.
- The stage registration label becomes `source-post readback (hard fields fail, prose report only)`.
- `AGENTS.md` §4/§8 rows update from "report-only by design (all fields)" to the split
  (rule 3c — the row names exactly what changed).

## Impact

- **Specs:** `validate-source-post-readback` (MODIFIED requirement: report-only → split verdict).
- **Code:** `scripts/validate.py` (constants, `check_source_post_readback`, registration label).
- **Tests:** `tests/test_source_post_readback.py` — the old blanket "never fails" test is
  replaced by paired tests: a planted hard-field drift FAILS the data stage; a planted
  prose drift stays report-only; the declared field sets are pinned.
- **Data:** none (live residue measured 0 today, so the gate lands green).

## Not covered

- Promoting `engine_min_version` to the gate — it stays report-only until a separate change
  measures its precision (issue #789's explicit alternative).
- Search-side ingest refusals for contradicted hard-field values (ingest is #531's other half;
  this change is the validator gate only).
