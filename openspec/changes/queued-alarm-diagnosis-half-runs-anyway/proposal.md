# Proposal: queued-alarm-diagnosis-half-runs-anyway

Issue: #1024 — "the queued-alarm job skips its diagnosis half when the sweep-alarm step goes red first"

## Why

Rule 6r promises a red main pipeline is DIAGNOSED (log read, error block extracted, issue filed,
ledger landed). Measured the opposite on dispatch run 43698769068 (2026-11-15): step 4
(`make sweep-alarm`) exited 2 because the newest scheduled sweep (run 43147959554, 2026-11-12 —
the `openspec-record-pr` refusal class since fixed by #952) was a FAILURE, and GitHub then
SKIPPED every later step — `make freshness-alarm`, `make master-alarm`, `make
pipeline-failure-issue`, the ledger-landing step, `make owed-rows-check` and
`make check-branch-protection`. Run 43147959554 has no ledger row (`grep -c 43147959554
data/pipeline_failures.json` → 0) and no filed issue; the #969 re-diagnosis pass stays unexecuted,
which keeps issue #968 cycling `refine` verdicts. One red detector silently disarms the whole
alarm job — the exact quiet state rule 6r exists to remove.

## What Changes

- `.github/workflows/queued-alarm.yml`: every detector/diagnosis step of the `alarm` job (from
  the queued-run report through `check-branch-protection`) gains
  `if: ${{ !cancelled() }}`, so a sibling's verdict never skips a detector. The job still
  concludes red — a failed step keeps its own conclusion — and the `guard` job (a `needs:`) still
  gates the whole job.
- `tests/test_queued_run_alarm.py` gains
  `test_every_alarm_step_runs_whatever_a_sibling_decided`: one verifier lists unguarded
  `run: make` steps in the `alarm` job; it returns nothing on the shipped workflow and flags
  every step on a planted copy with the `if:` lines removed — proving the pin fails on the old
  shape (rule 6c).

## Impact

- Capability: `alarms` (the same capability as `master-alarm-push-signal` and
  `pipeline-failure-rediagnose-822`).
- Pipeline: `queued-alarm.yml` only. No `make` target changes; no data or contract changes.
- After merge, the next `queued-alarm` delivery runs the filer over run 43147959554 inside its
  window (default 192 h), files the issue, lands the ledger PR, and executes the re-diagnosis
  pass that issue #968 waits on.

## Not covered

- The sweep-alarm verdict itself (a stale FAILED delivery is a TRUE alarm — rule 6s cadence).
- Any repair of the November-12 sweep failure (already fixed by #952); this change only makes the
  filer actually see and record it.
- Other pipelines' step ordering (their jobs' steps are already `if:`-free but their alarm chains
  are not single-job — out of scope).
