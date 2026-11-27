# Proposal: qa-validate-timeout-1845

Issue: #1845
PR: #1846

## Why

PR #1837's qa-validate run `46049222481` ended with `validate` `conclusion=cancelled`
at exactly 30 minutes even though its unit suite had passed 124/0 and the guard,
closure and live-smoke jobs were green. The ceiling is the job-level
`timeout-minutes: 30` at `.github/workflows/qa-validate.yml:131`, so a run that
would otherwise go green never reaches the auto-merge gate.

## What Changes

- Raise ONLY the `validate` job's `timeout-minutes` from `30` to `45` in the
  shipped `.github/workflows/qa-validate.yml` (one line).
- Add one real-logic assertion to the existing workflow-guard module
  (`tests/test_workflow_guards.py`) that reads the SHIPPED YAML and pins
  `validate.timeout-minutes == 45`; it fails on the base value 30 and passes on
  the fixed value. Wire it into that module's `main()` so CI executes it.

## Impact

- `.github/workflows/qa-validate.yml` — one line, the `validate` job's timeout.
- `tests/test_workflow_guards.py` — one helper and one test function, called from
  `main()`; existing workflow-guard coverage is untouched.
- `findings/1845.md` and `openspec/changes/qa-validate-timeout-1845/` plus a
  regenerated `OPENSPEC.md`.

## Not covered

- No `schedule:` edit, no other job's timeout, no new workflow, no label change.
- No data, README, schema, pipeline or rulebook change.
- No change to what `validate` checks — only how long it may run.
