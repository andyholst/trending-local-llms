# Proposal: gap-files-once-per-dimension

Issue: #472 (the measured re-file loop)

## Why

The post-refresh gap analysis files ONE issue when the gap SET changed vs
`data/gap_baseline.json`. The set was **per model**
(`missing:storage_offload:<model-id>`), so every model the store gained that lacked a
dimension GREW the signature — and a grown signature is indistinguishable from a new gap.

Measured: **12 `storage_offload` issues since 2026-10-15** — #266 (31 models), #329 (38),
#347 (39), #364 (41), #376 (38), #395 (40), #415 (40), #456 (40), #460 (59), #466 (42),
#472 (59) — six of them open right now, the rest closed by the implementer's own verdict
(`agent:closed`, "duplicate / cannot be implemented") and **re-filed the next morning**
because the count had moved again.

The chain cannot converge: it files a *data* gap (the store lacks a footprint key) as an
*implementation* issue, the implementer correctly refuses to invent footprints, and the filer
re-files the identical dimension tomorrow. Twelve issues, one dimension, zero data gained.

## What Changes

- **The signature is one entry per DIMENSION**, never per model:
  `contract:<key>` / `missing:<key>` / `unstructured:<key>`.
- **The per-model detail is preserved** in the report and the issue body (`missing[key]` is
  still the list of model ids, `render()` still prints them), so a human sees which models and
  how many — the count just stops being an ISSUE-TRIGGERING fact.
- **A dimension still files once and stays one issue** until it closes: `already_filed()`
  (open-issue marker dedup) is untouched, and a genuinely NEW dimension still changes the
  signature and files.
- **Tests updated** (`tests/test_data_gap_analysis.py`): the signature covers the dimension,
  not a model; a model joining an existing gap does NOT change the signature (the fix); both
  models are still named in the report; a real change still exits 1 under `--check`.

## Impact

`scripts/data_gap_analysis.py` (the signature line + its comment), `tests/test_data_gap_analysis.py`,
`OPENSPEC.md`, this change. No new target, stage, job or image.

## Not covered

- **The 12 existing issues are not mass-closed here.** Closing 11 as duplicates is a decision
  about the backlog, not about the code; the fix stops the *new* filings, and the open ones stay
  a human call (the implementer already closed the ones it judged duplicates).
- **`storage_offload` is still a data gap.** This change stops the re-filing, not the gap: the
  search legs must capture the footprint for the dimension to close.
