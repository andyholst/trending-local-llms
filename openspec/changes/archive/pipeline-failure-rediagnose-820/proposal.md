# Proposal: pipeline-failure-rediagnose-820

Issue: #820
PR: #967

## Why

Issue #820 was filed UNDIAGNOSED: when `make pipeline-failure-issue` swept run
41788683672 (queued-alarm, schedule 2026-11-04), the log fetch was refused by terminal
escape sequences — the exact defect issue #923 fixed — so the issue carries only "the log
could not be read" and its ledger row has `fix_pr: null`, `guard: null`. A closed marker
issue whose ledger entry names no fix PR and no guard test is exactly what
`make pipeline-failure-guard-check` refuses (rule 6r), so #820 can never close as it
stands. Now that the log reader works (issue #923), the run's own job log is readable: its
alarm job died on `make: *** [Makefile:1333: sweep-alarm] Error 1` with the verdict line
"[sweep-alarm] FAIL: the newest delivery is only 0.3 h old but concluded 'in_progress'" —
the measured **in-flight misgrade** class that PR #806 (issue #801) already fixed, guarded
by `tests/test_sweep_alarm.py`. The failure is fixed and guarded; only the diagnosis is
missing. Closing a stale issue must quote proof (issue #494/#766) — this change writes that
proof into the ledger.

## What Changes

- `data/pipeline_failures.json`: the row for run 41788683672 is raised append-only with
  `error_excerpt` (the log's own bounded error block), `targets: ["sweep-alarm"]`,
  `fix_pr: 806`, `guard: "tests/test_sweep_alarm.py"`, `rediagnosed_utc` and a
  `rediagnosis_note`; the original `undiagnosed` field is KEPT (rule 3b — a value is never
  removed or shrunk).
- `tests/test_pipeline_failure_guard.py`: a new test asserts the raised row (fix PR named,
  guard test on disk, diagnosis names the in-flight verdict line, `undiagnosed` still
  present) and that the committed ledger passes the real gate with issue #820 CLOSED — the
  exact post-merge CI shape.

## Impact

- Capability: `alarms` (the pipeline-failure ledger, rule 6r).
- Data: `data/pipeline_failures.json` (one row raised, append-only).
- Tests: `tests/test_pipeline_failure_guard.py` extended.
- Issue #820 closes on this PR's merge; `make pipeline-failure-guard-check` stays green
  because the closed row names fix PR #806 and a guard test that exists in `tests/`.

## Not covered

- The 13 other UNDIAGNOSED ledger rows (issues #821–#833) are NOT re-diagnosed here — each
  error class needs its own attribution to a merged fix PR + guard test. This run's
  `findings.md` files that follow-up work (rule 6g); the sweep picks them up one per week.
- No change to `scripts/pipeline_failure_issue.py` or the gate script — the filer's log
  reader was already fixed by issue #923; this change repairs the DATA that the old reader
  left behind.
