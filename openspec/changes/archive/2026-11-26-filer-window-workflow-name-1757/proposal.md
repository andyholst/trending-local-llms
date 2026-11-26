# Proposal: filer-window-workflow-name-1757

Issue: #1757

## Why

`make pipeline-failure-issue` writes titles like `tech-debt: None / validate failed (run …)` for runs found by the paginated window walk. 55 open issues carry that `None /` shape. The window walk feeds real REST `actions/runs` rows into `_project_run`, whose `_RUN_ROW_FIELDS` (`scripts/pipeline_failure_issue.py:257`) projects `workflowName` from a `workflow_name` key the REST endpoint never returns — the workflow name lives in `name`:

```text
gh api 'repos/andyholst/trending-local-llms/actions/runs?per_page=1' --jq '.workflow_runs[0]|{name,workflow_name}'
{"name":"refresh-bot","workflow_name":null}
```

`workflow` then flows into ledger rows (`:789`, `:815`, `:2129`, `:2188`), issue bodies (`:1270`) and titles (`:1319`). Worse, the dispatch-only tracking predicate (`:1188`, `workflow in DISPATCH_ONLY_PIPELINES`) cannot match `None`, so a concluded-bad dispatched run of a dispatch-only pipeline is silently dropped instead of filed (rule 6r/6t). The test stub (`tests/test_pipeline_failure_issue.py:76-85`) emits the same non-existent key, which is why the suite stays green.

## What Changes

- Project `workflowName` from the REST `name` field in the ONE `_RUN_ROW_FIELDS` mapping (rule 6d).
- Correct the canned REST fixture to the real external spelling (`name`, no `workflow_name`).
- Add a regression proving a window-walk REST row with only `name` yields a workflow-named title and ledger row (not `None`) and that a dispatch-only run is tracked. Prove it RED on the pre-change script.

## Impact

Capability: `pipeline-failure-filer`. One source field in one mapping, one fixture correction and one regression in an already-rowed test module. No data value invented, no contract, no workflow, no protected `AGENTS.md` rule edit, no CI dispatch.

## Not covered

- The other failure-class defects named on the `None /` issues (cancellation classification, master-move race, FILLER chatter, SIGPIPE, buildkit lock) stay tracked on their own issues.
- No ledger row is rewritten: rule 3b keeps existing `workflow: null` values; only new rows gain the correct name.
