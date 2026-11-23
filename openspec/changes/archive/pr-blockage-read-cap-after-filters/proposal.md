# Proposal: pr-blockage-read-cap-after-filters

Issue: #1405
PR: #1443

## Why

`scripts/pipeline_failure_issue.py::pr_triggered_failures` bounds the sweep with
`bound_pr_block_runs(runs)` applied to the WHOLE newest-first `gh run list --limit 30` page
before it filters to concluded-bad runs and to branches that are still open PRs. The cap was
added by issue #1174 to stop a fleet-wide outage costing one log read per red job, and #1264 made
the skipped count visible. But bounding the raw page spends the budget on green and merged runs:
measured on this host (2026-11-23, window 192 h) the pass announced
`log budget 8 run(s); skipped 22 run(s) beyond the cap`, so every red run on an open branch sat
past the cap and a shape blocking several open PRs was never grouped — exactly the #1164 failure
("a stale pin blocks EVERY open PR") returning the moment newer green runs fill the page.

## What Changes

- `pr_triggered_failures` applies the THREE cheap filters first — `conclusion in BAD_CONCLUSIONS`,
  `headBranch in open_pr_branches(repo)`, and `createdAt >= now - window_hours` — through ONE new
  pure helper `pr_block_candidates()`, and only then calls the unchanged `bound_pr_block_runs()`
  on that candidate list. The cap therefore bounds LOG READS, not relevance: at most
  `PR_BLOCK_MAX_LOG_READS` runs' logs are fetched, and they are the runs that can actually be a
  blockage.
- The skipped count stays announced (`stats["pr_block_runs_skipped"]`) and now means "red runs on
  open branches left for a later sweep", which is what the number hid before.
- `record_pr_blockages` computes `open_pr_branches` ONCE and passes it into the collection pass,
  so the pre-filter adds no extra `gh pr list` call.
- Tests: extend `tests/test_pipeline_failure_issue.py` — a behavioural guard that plants
  `PR_BLOCK_MAX_LOG_READS` newer GREEN runs ahead of two red runs on open branches and asserts
  the blockage IS grouped (RED on the base script, where the cap keeps only the green runs), plus
  the source-shape needle moved to the new call site.

## Impact

No change to the ledger shape, the marker set, the filed body, the grace window or any workflow.
The selection order inside one function changes; `bound_pr_block_runs()` keeps its own contract
(newest `cap` of whatever list it is given). A red run on an open branch can no longer be dropped
by the cap merely because newer green runs filled the page.

## Not covered

- No change to `PR_BLOCK_MIN_PRS`, `PR_BLOCK_GRACE_HOURS` or `PR_BLOCK_MAX_LOG_READS`.
- No rulebook edit: the §8 row this change owes under rules 6c/3c is declared as an owed row
  (rule 6g) and lands from the ledger by an attended run.
- No workflow, schedule or cron edit; no merge and no master push.
