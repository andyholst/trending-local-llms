# Proposal: workflow-concurrency-groups-1560

Issue: #1560
PR: #1564

## Why

Owner directive 2026-11-24: **a new push must stop the previous CI run for that PR.**
Measured on `origin/master`: `qa-validate.yml` and `pr-closure.yml` are the only two of
the twelve workflows with NO top-level `concurrency:` block, and they are exactly the two
PR pipelines that pile up. Measured on #1434, six master tips re-ran `qa-validate` while
earlier runs were still queued, and the board has held five concurrent `qa-validate` runs
at once. A superseded head keeps burning runner minutes and buries the current verdict
under stale checks.

## What Changes

- `.github/workflows/qa-validate.yml`: a top-level `concurrency:` group keyed by
  `github.workflow`, the event name and `github.event.pull_request.number`, falling back
  to `github.ref` for events that carry no PR number (`push`, `workflow_dispatch`);
  `cancel-in-progress: true`.
- `.github/workflows/pr-closure.yml`: the same shape (`pull_request`, `issues`, `push`).
- All twelve workflows carry a documented group: a comment attached directly above the
  block naming its scope and its cancel choice. The other ten keep their existing values
  unchanged — each stays scoped to its own purpose.
- `tests/test_workflows.py::test_every_workflow_declares_an_explicit_scoped_concurrency_group`
  locks the shape: all twelve blocks explicit, the two PR pipelines cancelling per PR,
  the rest serialising, no group shared across purposes, and the real templates resolved
  to distinct groups per PR, per purpose and per pipeline.

## Impact

No trigger changes: nothing is scheduled and no `schedule:` is edited. No gate is weakened
and no job loses a needed scope — `cancel-in-progress: true` acts only inside one group,
so another PR's or another purpose's run is never touched. The existing per-job groups in
`qa-validate` (`auto-merge-<pr>`, the keepers) are untouched.

## Not covered

- No new cron, no GitHub Actions schedule, no merge, no master push, no new make target.
