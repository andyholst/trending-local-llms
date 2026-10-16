# Proposal: data-gap-baseline

Issue: #174

## Why

`scripts/data_gap_analysis.py` declares `--write-baseline` ("record the current gap
signature as the baseline (no issue)"), and **nothing reaches it**: `grep -rn
"write-baseline"` over the Makefile, `.github/workflows/**`, `scripts/**` and
`tests/**` returns only its own declaration. The only writer of
`data/gap_baseline.json` is `--issue`, and it writes the baseline **only when it
files**.

Rule 6d makes a reachable-only-by-accident entry point a defect, and this one has a
real cost: a baseline write reaches `master` only through the refresh PR, so a
rebase or a refresh PR closed before it merged loses it, and the documented ability
to re-record the baseline cannot be exercised — which means it cannot be tested
either. The flag was dead code with a live purpose.

## What Changes

- **`Makefile`** — `data-gap-baseline`, the filer's repair half: runs
  `python3 scripts/data_gap_analysis.py --write-baseline`. **Host-side** like
  `data-gap-issue` (it writes `data/gap_baseline.json` as the caller, never as root
  through the container mount), and **deliberately NOT in the refresh pipeline**:
  run there it would set the baseline to the current gap set on every refresh and
  silently stop the analysis filing anything.
- **`tests/test_data_gap_analysis.py`** — the wiring test now asserts the target is
  defined, runs the flag, is host-side and leaves no `_data-gap-baseline` wrapper
  behind (rule 6d); a new test drives `--write-baseline` for real and asserts the
  file it writes **equals `analyse(store)`'s signature** — the contract `changed()`
  reads — and that a run against it then sees no change and files nothing.
- **`scripts/data_gap_analysis.py`** — the usage block documents the flag and both
  baseline writers (the module docstring had never listed it).
- **`ARCHITECTURE.md`** (rule 6h) — the target in §3's table.
- **`AGENTS.md` §8** — the existing `tests/test_data_gap_analysis.py` row names the
  new guard.

## Impact

`Makefile` (one target), `scripts/data_gap_analysis.py` (docstring),
`tests/test_data_gap_analysis.py` (wiring + behaviour), `ARCHITECTURE.md`,
`AGENTS.md` (§8 row), the OpenSpec change + `OPENSPEC.md`. No data file changes:
`data/gap_baseline.json` is untouched by this change.

## Not covered

- **Putting `data-gap-baseline` in the refresh pipeline.** It is a repair a human
  runs after a lost baseline, not a step of the refresh — running it automatically
  would accept every gap set as the baseline and silence the filing the stage
  exists for.
- **Changing when `--issue` writes the baseline.** It writes on filing, which is
  what makes a second run before the PR merges a no-op; that behaviour is the one
  the dedup test (#157) locks and is not in scope here.
