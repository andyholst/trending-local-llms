# Proposal: filers-label-rest-1766

Issue: #1766
PR: fix/filers-label-rest-1766

## Why

PR #1771's qa-validate reds on the OpenSpec lifecycle step
(`make openspec-archive-check PR=1771`) because no OpenSpec change on the PR's
tree binds Issue: #1766. The lifecycle guard's change-required prong (issue
#1109) requires every issue the PR closes to be named by at least one active
or archived change, and this triage/lifecycle fix adds that OpenSpec change.

## What Changes

- Create a new active OpenSpec change `openspec/changes/filers-label-rest-1766/`
  that binds `Issue: #1766` and declares `PR: fix/filers-label-rest-1766`.
- Add a capability spec and one completed task under the change.
- Regenerate `OPENSPEC.md` from `openspec/changes/**` via
  `make openspec-index`; the index file is regenerated, never hand-edited.

## Impact

No data store, README, engine measurement or pipeline change. This is a
contract-only change: one new change directory plus the regenerated root index.

## Not covered

- No merge to `master`; no push of the underlying filers/label work.
- No local `make test` or `make validate`.
