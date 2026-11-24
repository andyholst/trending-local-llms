# Proposal: filer-skip-cancelled-push-runs

Issue: #1669
PR: #1673

## Why

A `push`-to-`master` run that GitHub CANCELLS is superseded by the newer push that replaced it
(the repo's `#1560` concurrency behaviour): it never concluded a delivery, its jobs carry no error
text and their logs are gone (`gh: HTTP 404`). The master/schedule half of the failure filer still
treats every `cancelled` run as a tracked failure (`BAD_CONCLUSIONS`), and its error-class grouper
has no empty-signature skip, so a busy master files ONE content-free `UNDIAGNOSED` issue quoting
only the filer's own log-read 404 — measured on 2026-11-24: `WOULD FILE: class da39a3ee5e6b on
9 run(s) … error_lines=log fetch for job 138574538758 failed twice: gh: HTTP 404`, all nine
`event=push`/`headBranch=master`/`conclusion=cancelled`. The PR-blockage half already refuses
exactly this shape (#1604); rule 6r forbids filing an issue with no failure text.

## What Changes

- `scripts/pipeline_failure_issue.py`: a `push`-to-`master` run that concluded `cancelled` AND
  whose jobs yielded no failing step, no `make` target and no readable error block is not a
  tracked failure — it is superseded, not a failure. A cancelled run whose log DID yield a
  diagnosis still files (issue #1615), and a cancelled `schedule`/dispatch run is still a dropped
  delivery (`BAD_CONCLUSIONS` unchanged for those events).
- The skip is ANNOUNCEMENT-carrying, never silent: the sweep prints how many superseded runs it
  dropped, in `--dry` as well as live.
- `tests/test_pipeline_failure_issue.py`: RED-first guards for the nine-run shape, for the
  readable-diagnosis and `schedule` counterexamples, and for the dry-run announcement.
- `ARCHITECTURE.md` §10 regenerated (`make architecture-refresh`) for the script-docstring touch.

## Impact

No data format, contract, image or workflow wiring change; the ledger keeps its shape (the shipped
81 rows are untouched, rule 3b). A genuinely red `failure` run with an unreadable log still files
`UNDIAGNOSED` loudly, and a cancelled `schedule` run is still tracked. Only the content-free
superseded-push class stops being filed.

## Not covered

- The PR-blockage half (already correct via #1604) and the queued/ghost alarms, which own
  never-started and stuck runs.
- Any change to `BAD_CONCLUSIONS` itself, to the ledger schema, or to the guard gate.
- The `AGENTS.md` §8 row for the extended test module: a protected rulebook file, carried as a
  rule-3c owed row instead of a headless edit.
