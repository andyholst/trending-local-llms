# Proposal: pipeline-failure-rediagnose-822

Issue: #822
PR: #977

Issue #822 was filed UNDIAGNOSED: the filer's log reader (the defect issue #923 fixed) refused
run 41922211098's alarm-job log, so its ledger row carries `fix_pr: null`, `guard: null`. A
CLOSED marker issue whose row names neither is what `make pipeline-failure-guard-check` refuses
(rule 6r), so #822 can never close as it stands. The log is readable now and names the exact
failure: `[sweep-alarm] FAIL: the newest delivery is only 0.2 h old but concluded
'in_progress'` — the measured **in-flight misgrade** class PR #806 (issue #801) already fixed
and `tests/test_sweep_alarm.py` already guards. The failure is fixed and guarded; only the
diagnosis is missing. This mirrors the sibling re-diagnoses of run 41788683672 (#820, PR #967)
and run 41860616772 (#821, PR #974).

## What Changes

- `data/pipeline_failures.json`: the row for run 41922211098 is raised append-only with
  `error_excerpt` (the log's own bounded error block), `targets: ["sweep-alarm"]`,
  `fix_pr: 806`, `guard: "tests/test_sweep_alarm.py"`, `rediagnosed_utc` and a
  `rediagnosis_note`; the original `undiagnosed` field is KEPT (rule 3b).
- `tests/test_pipeline_failure_guard.py`: a new test asserts the raised row and the exact
  post-merge gate shape (issue #822 CLOSED → gate exit 0) against the committed ledger.

## Impact

- Capability: `alarms` (the pipeline-failure ledger, rule 6r).
- Data: `data/pipeline_failures.json` (one row raised, append-only).
- Tests: `tests/test_pipeline_failure_guard.py` extended.
- Issue #822 closes on this PR's merge with a guarded ledger row.

## Not covered

- Runs 41956933757 (#824) and 43049550731 (#829) are the SAME class and are re-diagnosed by
  issue #976's change (finding filed by PR #974); run 41929086636 (#823) is a different error
  class (`duplicate model ids` validation failure) needing its own diagnosis — tracked by the
  finding filed as issue #975 (rule 6g).
- No change to `scripts/pipeline_failure_issue.py` or the gate script — the filer's log reader
  was fixed by issue #923; this repairs the DATA the old reader left behind.
