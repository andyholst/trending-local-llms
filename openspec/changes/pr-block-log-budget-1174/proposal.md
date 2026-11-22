# Proposal: pr-block-log-budget-1174

Issue: #1174

## Why

`pr_triggered_failures` reads a log for every failed job of every blocked PR. `MAX_LOG_TAIL_BYTES` bounds one log's bytes but not the number of reads: 20 red PRs on one shared defect cost 20 log fetches on every sweep, and shape grouping needs them all before it can claim a shared shape.

## What Changes

- Add `PR_BLOCK_MAX_LOG_READS` and a pure `bound_pr_block_runs` seam; `pr_triggered_failures` only reads logs for the capped runs and records the skipped count.
- `record_pr_blockages` announces the budget and the skipped count in the sweep line.
- Extend `tests/test_pipeline_failure_issue.py` with a guard that fails if the cap or the announcement is removed.

## Impact

- One script, one test module, one OpenSpec change. No workflow, make target, data format or CI dispatch change.

## Not covered

- No change to the 24 h grace, dedup markers or PR-blocking threshold.
