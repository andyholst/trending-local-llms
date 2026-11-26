# Proposal: none-title-backfill-1759

Issue: #1759

## Why

The board carried 55 open issues titled `tech-debt: None / …`. The `None` was a projection bug fixed in #1757 / PR #1758 (REST `actions/runs` serves the workflow name in `name`, never `workflow_name`), but that fix only stops FUTURE filings: the already-filed issues kept broken titles and the matching ledger rows in `data/pipeline_failures.json` kept `workflow: "None"` (51 rows) or no correct name. A board whose titles say `None` cannot be searched by pipeline, so the next reader re-derives the run from the page.

## What Changes

- Repair the title and body of each of the 55 issues in place: replace `None /` with the real workflow name read from the run id in its registered `pipeline-run-failure` marker via REST `.name`. Host-side `gh api -X PATCH`, no filer re-run (dedup would skip existing issues), no CI dispatch.
- ADD the `workflowName` key to every ledger row through an additive pass that preserves every existing key and value byte-for-byte (rule 3b: keys may only be ADDED, never removed/renamed, no value shrunk).
- Add one guard to the existing `tests/test_pipeline_failure_issue.py` module asserting every shipped ledger row carries a real workflow name and the #1757 projection has not regressed; prove it RED on the pre-backfill ledger.

## Impact

Capability: `pipeline-failure-filer`. One additive data backfill (85 ledger rows gain one key), 55 in-place board title/body edits, one regression in an already-rowed test module. No workflow, no new make target, no contract, no protected `AGENTS.md` rule edit by this headless leg (the §8 row extension is declared as an owed row), no CI dispatch, no merge.

## Not covered

- The distinct failure classes named on those 55 issues (SIGPIPE search legs, buildkit layer lock, openspec index drift, etc.) stay tracked on their own issues; this change repairs ONLY the broken workflow-name projection.
- No existing ledger value is rewritten: the legacy `workflow` spelling (including its historical `None` strings) is kept; only the new `workflowName` key is added.
- Rule-3c sign-off for the owed `AGENTS.md` §8 row is a human act; this leg leaves it blocked, not silently written.
