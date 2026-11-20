# pr-triggered-failure-ledger — a PR-blocking pipeline failure is recorded, and its fix is gated

Issue: #1164

## Why

A stale pin blocks EVERY open PR's `auto-validate`/`auto-merge` at the same step, which is a
larger outage than one red scheduled sweep — yet the ledger recorded nothing. Measured:
qa-validate run 44651246625 (PR #1159) and run 44651246366 (PR #1158) both died at
`Prepare runner images` with `the installed agent is NOT the pinned version: pinned 0.23.2,
installed 0.23.3`, and `grep -c "44651246625\|44651246366" data/pipeline_failures.json`
answered `0`; `make pipeline-failure-guard-check` on `master` reported nothing. The filer's
window walks main-pipeline runs on a push to master or a scheduled delivery, and a
`pull_request`-triggered run is neither.

## What Changes

- `scripts/pipeline_failure_issue.py` gains a PR-blockage pass riding the SAME
  `make pipeline-failure-issue` sweep: it walks `--event pull_request` runs of the main
  pipelines, groups them by a normalised `failure_shape` (`failure_shape` — failing step names +
  the `make` targets the log names + the error block with run ids/SHAs/counts collapsed), and
  when one shape blocks **two or more OPEN pull requests** files ONE issue for the group's
  earliest run and appends the row with the ADDED keys `trigger`, `failure_shape`,
  `blocked_prs`, `pr_count` (rule 3b: every existing key survives).
- `scripts/pipeline_failure_guard_check.py` goes RED on a recorded PR-blockage row whose fix
  has not landed within `PR_BLOCK_GRACE_HOURS` (24 h), on an injected clock; inside the grace
  it is reported, and a landed `fix_pr` + `guard` clears it through the normal attribution path.
- `AGENTS.md` §6r names the pass and the new refusal (rule 3c: a review-required diff, and the
  issue carries the sign-off comment).
- Tests: `tests/test_pipeline_failure_issue.py` (shape normalisation, grouping, the real sweep
  end to end against the stub `gh`, idempotence, `--dry`) and
  `tests/test_pipeline_failure_guard.py` (both sides of the grace, the ISO8601Z spelling).

## Impact

- No new make target, pipeline job or image: the pass is bundled into `make
  pipeline-failure-issue`, which `queued-alarm.yml` already runs (rule 6d).
- Additive ledger keys only; no existing row is rewritten (rule 3b).
- Not covered: the queued-alarm's own detector for a still-RUNNING PR run (that is its job), and
  any blockage that hits fewer than two open PRs (one red PR is that author's own noise).
