# Proposal: pr-block-grace-derived-1176

Issue: #1176 — "The 24 h grace is a guess, and it is the only thing standing between
'reported' and 'red'" (tech-debt, surfaced from PR #1170).
PR: #1289

## Why

`PR_BLOCK_GRACE_HOURS = 24` in `scripts/pipeline_failure_issue.py` is a bare literal with no
measurement behind it. `make pipeline-failure-guard-check` uses it as the single boundary between
"a PR-blocking failure is still being repaired — report it" and "the blockage has no fix — go
RED on every open PR". A threshold chosen by feel can be argued about on exactly the thread
where the fleet needs agreement, and a reader cannot tell whether 24 h protects a real repair
window or merely hides a stale pin for a day. The measured #1164 outage (qa-validate runs
44651246625 / 44651246366) was a stale pin that blocked every open PR's `auto-merge` and was
fixed by a pin raise the same day — so the value is defensible, but its provenance is invisible
to both the code and the guard.

## What Changes

- `scripts/pipeline_failure_issue.py` introduces `PR_BLOCK_REPAIR_WINDOW_HOURS = 24`, documents
  that the basis is the measured same-day #1164 repair (not a sweep cadence — `queued-alarm.yml`
  is dispatch-only after issue #1029), and assigns `PR_BLOCK_GRACE_HOURS` FROM that named window.
  The numeric value stays 24 h; only its provenance and derivation change.
- `tests/test_pipeline_failure_guard.py` gains
  `test_the_pr_block_grace_is_derived_from_its_stated_repair_window`, registered in `main()`,
  which refuses a bare-literal grace, a comment without the measured basis, and a gate that
  reads a different seam. It is RED on the pre-change file (three failed checks on the old
  literal), proving the guard locks the change.

## Impact

- Two files only: one product constant + its comment, one regression test. No Makefile target,
  workflow, image, data key or contract shape changes (rules 6b/6h/6m inventory unchanged).
- The guard's behaviour at 24 h is byte-identical; the existing PR-blockage report/red test
  (`test_a_recorded_pr_blockage_whose_fix_never_lands_is_red_after_its_grace`) still passes.
- One `AGENTS.md` §8 guard-row update is owed and review-required (rule 3c). This headless leg
  writes it as a `- [~]` blocked box and records the full row text in `findings.md` as an
  owed-row finding; a reviewer signs off on the rulebook diff before merge. The section and
  reason are already declared on issue #1176.

## Not covered

- No change to the 2-PR `PR_BLOCK_MIN_PRS` threshold, the ledger schema, the stamp/attribution
  passes, or the grace's numeric value.
- No new scheduled sweep or CI dispatch — cadence stays as issue #1029 left it.
- The stale "weekly, Wednesday" sentence in the module docstring is a separate finding, filed
  (not fixed) through `findings.md`.
