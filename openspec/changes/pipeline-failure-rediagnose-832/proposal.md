# Proposal: pipeline-failure-rediagnose-832

Issue: #832

## Why

Issue #832 is the auto-filed pipeline-failure diagnosis for queued-alarm run 43109817750:
its `alarm` job died on `make: *** [Makefile:1384: sweep-alarm] Error 1` with the verdict line
`[sweep-alarm] FAIL: the newest delivery is only 0.2 h old but concluded 'in_progress'` — the
measured **in-flight misgrade** class (issue #801): the alarm graded a weekly delivery that was
still `in_progress` (0.2 h old, under the in-flight cap) as a FAILED sweep. That failure class
was already fixed by PR #806 (issue #801) and is guarded by `tests/test_sweep_alarm.py`
(`test_an_in_flight_delivery_is_pending_not_a_false_red`). The ledger row for this run was
re-diagnosed on the sweep (issue #969) with the real `error_excerpt` and `targets`, but it was
never given the fix attribution: `fix_pr` and `guard` are still null. A CLOSED marker issue
whose ledger entry names no fix PR and no guard test is exactly what
`make pipeline-failure-guard-check` refuses (rule 6r), so #832 can never close as it stands —
while every identical-class sibling (#820/#821/#822/#824/#829) already carries
`fix_pr: 806` + `guard: tests/test_sweep_alarm.py`. The gap is the missing ledger attribution.

## What Changes

- `data/pipeline_failures.json`: the row for run 43109817750 is raised append-only with
  `fix_pr: 806` and `guard: "tests/test_sweep_alarm.py"` — the same landed fix + guard the
  identical-class siblings already name — its `targets` GROWN to the parseable target
  `sweep-alarm`, and `rediagnosis_note` extended to record the attribution. The original
  `undiagnosed` field and every existing value are KEPT (rule 3b — a value is never removed or
  shrunk; keys only added).
- `tests/test_pipeline_failure_guard.py`: a new test asserts the raised row (fix PR named,
  guard test on disk, in-flight verdict line in the excerpt, `undiagnosed` still present) and
  that the committed ledger passes the real gate with issue #832 CLOSED — the exact post-merge
  CI shape.

## Impact

- Capability: `alarms` (the pipeline-failure ledger, rule 6r).
- Data: `data/pipeline_failures.json` (one row raised, append-only, rule 3b).
- Tests: `tests/test_pipeline_failure_guard.py` extended.
- Issue #832 closes on this PR's merge; `make pipeline-failure-guard-check` stays green because
  the closed row names fix PR #806 and a guard test that exists in `tests/`.

## Not covered

- The other un-attributed ledger rows (issues #826/#827/#828/#831/#833, #1039–#1043) are NOT
  raised here — each error class needs its own attribution to a merged fix PR + guard test, and
  each is a separate change (rule 6g); this change's `findings.md` records those. No change to
  `scripts/` — the re-diagnosis logic already runs (issue #969) and the guard already enforces
  (rule 6r); this change repairs the DATA attribution the sweep left behind.
