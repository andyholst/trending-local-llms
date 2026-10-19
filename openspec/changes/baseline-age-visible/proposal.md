# Proposal: baseline-age-visible

Issue: #307 — `tech-debt: The gap baseline's age is written but never read, so a stale baseline is invisible until a duplicate issue appears`

## Why

`data/gap_baseline.json` is the dedup key of the whole data-gap chain: `changed()`
compares its `signature` with the current analysis, and a match means **no issue is
filed**. `write_baseline()` records `{"as_of": …, "signature": …}` — and nothing ever
read `as_of`. Measured on the repository: the baseline's `as_of` is written on two
paths (`--issue` and `--write-baseline`) and read on none (`grep as_of` finds only the
write).

The consequence is silent: a baseline left behind by a rebase or by a refresh PR that
was closed before merging keeps the gap set "unchanged" for as long as it sits there,
while the gaps it describes grow older — and the only signal is a *missing* issue, which
is indistinguishable from "there is nothing to file". Rule 6g's chain (`make data-gaps`
→ `make data-gap-issue`) then reports green every run.

## What Changes

- **`baseline_info(path, as_of)`** reads the recorded `as_of` and measures its age in
  days against *this analysis'* as-of (the store's `generated_utc`, so the number is
  deterministic rather than a wall clock). A missing file reports nothing; an
  unparseable stamp reports an unknown age instead of raising.
- **The report carries it**: `render()` prints
  `- baseline: recorded \`<as_of>\` (N day(s) before this analysis)` right under the
  header block, so the issue body and `make data-gaps` show which key was compared.
- **The run log carries it, loudly when stale**: the CLI always prints
  `[data-gaps] baseline: recorded … (N day(s) before this analysis)`, and when the age
  reaches `STALE_DAYS` (30) it prints `baseline is STALE … make data-gap-baseline
  re-records it` and adds the same sentence to the report's findings.
- **`tests/test_data_gap_baseline_age.py`** drives the real script (its `baseline_info`
  and `render`, and the CLI against the real store with a temp baseline): the age
  measurement, the render line, the stale shout with its fix, and the fresh case that
  must NOT be called stale.

Verified RED against the pre-change script (6 checks fail — no `baseline_info`, no
report line, no log lines) and GREEN after (`PASSED 15 | FAILED 0`).

## Impact

`scripts/data_gap_analysis.py`, a new `tests/test_data_gap_baseline_age.py`, this
OpenSpec change and the regenerated `OPENSPEC.md`. No make target, stage, job, image or
contract changes (`ARCHITECTURE.md` unchanged, rule 6h); the analysis stays report-only
and never fails a data PR.

## Not covered

- **Auto-re-recording a stale baseline.** Re-recording is a judgement (the gaps may
  legitimately be unchanged); the filer's `make data-gap-baseline` is the human's tool,
  and this change makes its absence visible rather than acting on its behalf.
- **The fresh-baseline case in CI.** `data/gap_baseline.json` on master is the file a
  refresh PR writes; no target re-dates it here, and the new test proves staleness is
  named instead.
