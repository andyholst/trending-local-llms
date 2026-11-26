# Proposal: filers-label-rest-1766

Issue: #1766
PR: fix/filers-label-rest-1766

## Why

`make openspec-check` (run by qa-validate's `validate` job on every PR) refuses an
active change that is neither bound to its issue nor declared exempt. PR #1771
(`fix/filers-label-rest-1766`) applies the REST label patch across the four issue
filer implementations, but the change that binds the branch to its issue was not
created: the OpenSpec lifecycle gate on the PR's tree reported no Issue line for
anything -- `openspec-binding-check` refuses it and `make openspec-check` goes
red before the implementation's guards could run. A change that records and
releases this binding must therefore exist on the PR's branch, holding
`Issue: #1766`, so that qa-validate's OpenSpec step accepts the PR.

## What Changes

- New active change at `openspec/changes/filers-label-rest-1766/`:
  - `proposal.md` -- the binding itself:
    `Issue: #1766`, `PR: fix/filers-label-rest-1766`, with Why
    (PR #1771's qa-validate OpenSpec lifecycle step refuses because no OpenSpec
    change names Issue: #1766), What Changes (this change), Impact and Not
    covered.
  - `tasks.md` -- a single checked checkbox (the sole task: create this change).
  - `specs/filers-label-rest-1766/spec.md` -- capability spec adding the
    `filer-label-rest-1766` requirement family: the other three issue filers
    (data-gap-analysis, file-findings, issue-review, issue-verdict) apply labels
    through the REST endpoint, with a stub-gh guard per module proving the
    GraphQL `addLabelsToLabelable` mutation is never attempted on a PAT-shaped
    credential.
- Regenerate `OPENSPEC.md` with `make openspec-index` (never by hand) so the
  index gains the new active change's row.

## Impact

- **OpenSpec index:** `OPENSPEC.md` gains one active row
  (`filers-label-rest-1766`), one issue (`#1766`), one PR
  (`fix/filers-label-rest-1766`).
- **Data:** none -- no model, measurement or contract value changes.
- **AGENTS.md:** §6f/§6g unchanged; this change is additive only.

## Not covered

- The REST label fix itself lives in PR #1771
  (`fix/filers-label-rest-1766`, issue #1766). This change only records the
  Issue/PR binding so the OpenSpec lifecycle gate accepts the PR's tree.
