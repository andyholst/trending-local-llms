# Proposal: tll-1764

Issue: #1764
PR: fix/filer-label-rest-1764

## Why

PR #1765's qa-validate `validate` job reds on the OpenSpec lifecycle step
(`make openspec-archive-check PR=1765`) because no OpenSpec change on the PR's
tree binds Issue: #1764. The lifecycle guard's change-required prong (issue
#1109) requires every issue the PR closes to be named by at least one active or
archived change; the filer REST-label fix landed without that OpenSpec change.

## What Changes

- Create a new active OpenSpec change `openspec/changes/tll-1764/` that binds
  `Issue: #1764` and declares `PR: fix/filer-label-rest-1764`.
- Add a capability spec and one completed task under the change.
- Regenerate `OPENSPEC.md` from `openspec/changes/**` via
  `make openspec-index`; the index file is regenerated, never hand-edited.

## Impact

No data store, README, engine measurement or pipeline change. This is a
contract-only change: one new change directory plus the regenerated root index.

## Not covered

- No merge to `master`; no push of the filer REST-label fix itself (PR #1765).
- No local `make test` or `make validate`.
