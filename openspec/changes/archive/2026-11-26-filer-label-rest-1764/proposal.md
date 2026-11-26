# Proposal: filer-label-rest-1764

Issue: #1764
PR: #1765

## Why

`make pipeline-failure-issue` is the ONE seam a host watcher uses to file a concluded-bad run (rule 6w/6r). On `asimov@omarchy` (authenticated with the owner PAT) at base `37c6d881`, that seam created issue #1763 with a correct five-section body, marker and scrubbed error block, then exited 2 at `scripts/pipeline_failure_issue.py:1333`:

```text
RuntimeError: gh issue edit 1763 failed (1): failed to update .../issues/1763:
  GraphQL: Resource not accessible by personal access token (addLabelsToLabelable)
```

`gh issue create --label tech-debt` exits 0 having applied nothing (#161), so the fallback at `:1333` is the only thing that applies the label. `gh issue edit --add-label` uses the GraphQL `addLabelsToLabelable` mutation, which the owner PAT cannot call (no Issues scope), while `gh api -X POST repos/<repo>/issues/<n>/labels` works with the SAME token. The result is exactly the starvation shape rule 6o names: an unlabelled `tech-debt` issue invisible to `issue-bot` and `issue-review-bot`, with the ledger row never appended.

## What Changes

- Replace the `gh issue edit … --add-label` fallback in `scripts/pipeline_failure_issue.py::file_issue` with the REST write `gh api -X POST repos/<repo>/issues/<n>/labels -f 'labels[]=tech-debt'`. The CI default-token path is byte-identical: REST works for both credentials.
- Extend `tests/test_pipeline_failure_issue.py` with a stub-gh case that refuses the GraphQL label mutation behind a fixture flag but answers the REST write, proving the filer files a LABELLED issue, appends the ledger row and exits 0 in one pass. Prove the guard RED on the pre-change script.

## Impact

Capability: `pipeline-failure-filer`. One call site in one script, one stub-gh fixture and one guard in an already-rowed test module. No data value invented, no contract, no workflow, no protected `AGENTS.md` rule edit, no CI dispatch, no merge. Existing ledger rows are untouched (rule 3b).

## Not covered

- The other filers that still use `gh issue edit --add-label` (`data_gap_analysis.py`, `file_findings.py`, `issue_review.py`, `issue_verdict.py`) are recorded as a separate finding, not fixed here (rule 6g).
- The three stale ACTIVE OpenSpec changes that red `openspec-archive-check` on master pushes (issue #1763) are keeper work, not this fix.
