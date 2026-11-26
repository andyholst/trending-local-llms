# Proposal: other-filers-label-rest

Issue: #1766

## Why

`gh issue edit … --add-label <L>` goes through GitHub's GraphQL
`addLabelsToLabelable` mutation. A host-side lane authenticated with the owner
PAT can create an issue but cannot call that mutation, so the filer files the
issue, then crashes before the label lands — leaving a `tech-debt` /
`data-gap-analysis` issue invisible to the queue that keys on that label (the
same starvation measured for the pipeline-failure filer in #1764 / PR #1765).
Four call sites still use that path on the fetched base:
`scripts/data_gap_analysis.py:1478`, `scripts/file_findings.py:277`,
`scripts/issue_review.py:137` and `scripts/issue_verdict.py:334`.

`gh api -X POST repos/:owner/:repo/issues/<n>/labels -f labels[]=<L>` uses the
REST endpoint instead. `repos/:owner/:repo` is gh's current-repo shorthand, so
it needs no explicit repo argument and works identically with the PAT and the
CI default token.

## What Changes

- Each of the four call sites applies its label through the REST label endpoint
  and keeps its existing post-write verification / loud refusal when the label
  still does not land.
- The four stub-gh test doubles model the PAT: `issue edit --add-label` is
  refused (GraphQL unavailable), the REST label write is answered, and each
  module's guard asserts that no GraphQL mutation was attempted.
- The guards are added to the modules' existing test files, not a new suite.

## Impact

- `scripts/data_gap_analysis.py`, `scripts/file_findings.py`,
  `scripts/issue_review.py`, `scripts/issue_verdict.py` — one REST label write
  each, no new make target, no workflow change.
- `tests/test_data_gap_analysis.py`, `tests/test_file_findings.py`,
  `tests/test_issue_review.py`, `tests/test_issue_triage.py` — stub updates and
  per-module guards.
- `AGENTS.md` §8 guard rows for these modules need the new guards named; that
  protected-file edit is rule-3c review-required and is declared as an owed row
  in `findings/1766.md`, not written by this headless leg.

## Not covered

- The `--remove-label` path in `scripts/issue_review.py:220` (a different
  GraphQL mutation, not named by this issue).
- The already-landed pipeline-failure filer fix in PR #1765.
- Label creation (`gh label create`) — unchanged; the failure is in applying a
  label that already exists.
