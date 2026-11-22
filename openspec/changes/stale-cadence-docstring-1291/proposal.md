# Proposal: stale-cadence-docstring-1291

Issue: #1291

## Why

`scripts/pipeline_failure_issue.py`'s module docstring still says the filer runs from
`queued-alarm.yml` "(weekly, Wednesday, like every other scheduled sweep — the weekly-cadence
pin)". `queued-alarm.yml` has been dispatch-only since issue #1029, and the grace comment
immediately below that sentence refuses a cadence basis for exactly that reason — so a reader of
the filer's own rationale sees a cadence that does not exist next to a comment that says so.
Issue #1032 closed the same drift class in `ARCHITECTURE.md`; this is the script's own copy.

## What Changes

- The module docstring names the filer's entry point as `queued-alarm.yml`, DISPATCH-ONLY since
  issue #1029 (no `on.schedule`), with no weekly or Wednesday claim.
- `tests/test_pipeline_failure_issue.py` gains a guard that reads the real module docstring and
  the real workflow `on:` block and fails on a weekly/Wednesday claim.

## Impact

- `scripts/pipeline_failure_issue.py` — module docstring only; no behaviour, target or contract.
- `tests/test_pipeline_failure_issue.py` — one new test in the existing module.
- `ARCHITECTURE.md` — regenerated (the §10 block carries one line per script from its own
  docstring, so a docstring edit stales it; rule 6h).

## Not covered

- The other cadence sentences in `scripts/` (each is its own finding).
- Any change to `queued-alarm.yml` itself (it is already dispatch-only).
