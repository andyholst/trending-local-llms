# Proposal: rediagnose-sweep-alarm-rows-976

Issue: #976
PR: #978

Finding #976 (filed by PR #974 while re-diagnosing #821) measured that ledger rows for runs
41956933757 (issue #824) and 43049550731 (issue #829) are UNDIAGNOSED copies of the SAME
already-landed error class: the sweep-alarm **in-flight misgrade** whose exact run ids AGENTS.md
§8 names as the measured shape of issue #801, fixed by PR #806 and guarded by
`tests/test_sweep_alarm.py`. Their job logs (readable since the issue #923 log-reader fix)
carry the identical verdict line `[sweep-alarm] FAIL: the newest delivery is only 0.2 h old but
concluded 'in_progress'`. Re-diagnosing them onto the landed fix collapses two open issues onto
proof instead of inventing new implementation work for a class that is already fixed and guarded
(rule 6r: a CLOSED marker issue needs its row to name `fix_pr` + `guard`).

## What Changes

- `data/pipeline_failures.json`: rows 41956933757 and 43049550731 are raised append-only with
  `error_excerpt`, `targets: ["sweep-alarm"]`, `fix_pr: 806`,
  `guard: "tests/test_sweep_alarm.py"`, `rediagnosed_utc` and `rediagnosis_note`; the original
  `undiagnosed` fields are KEPT (rule 3b).
- `tests/test_pipeline_failure_guard.py`: one new test asserting both raised rows and the
  post-merge gate shape with #824 and #829 CLOSED.

## Impact

- Capability: `alarms` (the pipeline-failure ledger, rule 6r).
- Data: `data/pipeline_failures.json` (two rows raised, append-only).
- Tests: `tests/test_pipeline_failure_guard.py` extended.
- Issues #824 and #829 become closeable on proof (the sweep's already-fixed verdict now has its
  ledger evidence); this PR closes the finding issue #976 itself.

## Not covered

- Run 41929086636 (issue #823) is a DIFFERENT error class (`duplicate model ids` validation
  failure) and keeps its own diagnosis work (finding filed by the #822 change, rule 6g).
- The sweep still decides the `agent:closed` verdicts for #824/#829 (the implementer never writes
  labels, rule 6j); this change supplies the proof those verdicts must quote.
