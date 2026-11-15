# Change: filer-rediagnosis-log-expiry-986

Issue: #986
PR: #1011

## Why

`make pipeline-failure-issue`'s re-diagnosis pass (issue #969) re-reads every still-UNDIAGNOSED
ledger row's log on each sweep. A row whose log stays UNREADABLE is retried on every weekly sweep
forever — GitHub Actions purges run logs after the retention window, so a row whose run ages out
(e.g. an old `queued-alarm` run) prints `rediagnose run <id>: jobs unreadable again` / `log still
unreadable` every sweep with no way to ever become done. The sweep log fills with permanent retry
noise, and a human skimming the report cannot tell "will heal next week" from "can never heal" —
exactly the signal UNDIAGNOSED exists to carry.

## What Changes

- `scripts/pipeline_failure_issue.py`'s re-diagnosis pass tracks an APPEND-ONLY
  `rediagnose_attempts` counter on each still-unreadable row (never removed or shrunk — the
  retention symptom is the two "cannot read the run" branches: `jobs unreadable again` and `log
  still unreadable`). After `MAX_REDIAGNOSE_ATTEMPTS` (3) still-unreadable sweeps it stamps a
  TERMINAL `log_expired` state (with the reason + `log_expired_utc`), printed loudly ONCE
  (`LOG EXPIRED run <id>: …`), and the row is EXCLUDED from the pending set — so the pending queue
  drains instead of retrying a log that can never be read. `undiagnosed` is KEPT (rule 3b); the two
  structural branches (no failed job, a readable log with no error-shaped line) stay
  reported-and-retried per #969, never expired.
- `--dry` previews the stamp (`WOULD EXPIRE run <id>: …`) and writes nothing.
- `scripts/pipeline_failure_guard_check.py` reports a `log_expired` row as its OWN shape (a drain,
  never red and never the closed-without-guard refusal) — there is no error class the log can ever
  produce, so closing its issue is legitimate.
- No new make targets / workflow changes: the behavior rides the existing weekly `queued-alarm.yml`
  call of `make pipeline-failure-issue` and the existing `make pipeline-failure-guard-check` step.

## Impact

- Capability: `alarms` (rule 6r filer + guard)
- Affected code: `scripts/pipeline_failure_issue.py`, `scripts/pipeline_failure_guard_check.py`,
  `tests/test_pipeline_failure_issue.py`, `tests/test_pipeline_failure_guard.py`,
  `ARCHITECTURE.md` (descriptive rows), `AGENTS.md` §8 (owed-row finding — protected)
- Not covered: other terminal states (e.g. a permanently-mismatched job name is intentionally kept
  retried per #969); a configurable retention bound.
