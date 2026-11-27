# Proposal: refresh-aggregate-timeout-1843

Issue: #1843
PR: #1844
**Capability:** `refresh-aggregate-timeout`

## Why

Refresh run 46044870416's `aggregate` job started at 18:00:22Z and was cancelled at
18:30:37Z — exactly 30 minutes — while in its `Commit + open PR` step. The four
`search` legs and all aggregate validation steps before it were green: the run was
killed by the job's configured `timeout-minutes: 30` at
`.github/workflows/refresh-bot.yml:527`, not by a failing check or a person. The
`search` job at :457 already had 60 minutes; the job that merges those legs,
validates the result and opens the data PR had half that budget.

## What Changes

- Raise ONLY the `aggregate` job's job-level `timeout-minutes` in the shipped
  `.github/workflows/refresh-bot.yml` from `30` to `60`, matching `search` at :457.
- Add one assertion to the existing workflow-guard module
  (`tests/test_workflow_guards.py`) that reads the SHIPPED YAML and pins
  `aggregate.timeout-minutes == 60`, wired into its `main()` so CI executes it.
  The assertion is RED on the base file (`['30']`) and GREEN on the fix.
- Record the evidence in `findings/1843.md` and bind this small OpenSpec change
  to issue #1843 and its PR; regenerate `OPENSPEC.md`.

## Impact

- Affected specs: `refresh-aggregate-timeout` (new requirement on the shipped
  aggregate job's wall-clock budget).
- Affected tests: `tests/test_workflow_guards.py` gains one test and one `main()`
  call; `tests/test_workflows.py` already checks every test is wired from `main()`.
- **Not covered:** no workflow schedule or trigger edit, no other job's timeout,
  no new workflow, and no data, README or schema change.

## Not covered

- The 60-minute value is a headroom fix for the measured cancellation, not a
  change to search leg budgets or to what the aggregate job does with its time.
