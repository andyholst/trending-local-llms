# Proposal: r-marker-pr

Issue: #1284

## Why

`scripts/watch_monitor.py` fetches `issues/comments`, `pulls/comments` and
`actions/runs`, but the `R:<run id>:<status>:<conclusion>` marker carries only a run id.
A lane handling an `R:` marker has no pointer from that run to the PR it belongs to, so it
cannot reliably check whether that PR's own thread got a new comment — yet the shared-board
protocol requires exactly that ("on `R:` it diagnoses the job and posts the result on the
thread"). Measured live: every PR-triggered run row already carries
`pull_requests: [{number: 1321}]` and `head_branch`, so the data is on hand and unused.

## What Changes

- `scripts/watch_monitor.py` resolves each changed run to its pull request number and
  appends it as an optional marker field: `R:<run id>:<status>:<conclusion>[:<workflow>][:<pr>]`.
  A push-triggered run (no `pull_requests`) keeps the existing shape, so every existing
  reader and every recorded marker stays valid.
- `tests/test_watch_monitor.py` plants a run with `pull_requests: [{"number": 1289}]` and
  fails on the run-only shape.

## Impact

One script and its guard. The marker protocol gains an optional trailing field; the
rulebook's marker list and the §10 inventory are refreshed in the same change.

## Not covered

- Walking the PR's comment thread inside the monitor: the monitor stays a change detector
  and hands the PR number to the woken lane, which reads the thread.
- A run that belongs to several PRs (a matrix dispatch): the first `pull_requests` entry is
  used, matching what `actions/runs` reports for this repo's single-PR pipelines.
