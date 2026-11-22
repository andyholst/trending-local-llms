# Proposal: openspec-merge-tree-1239

Issue: #1239 (measured on origin/master `cebd71c7`)

## Why

`qa-validate` checks out PR HEAD for the OpenSpec gate (#432), so each PRs index can be
correct for its own base while the eventual merge lands a count generated one archive
earlier. Measured: count 394 vs 395 archived on disk, all rows present; keeper PR #1223
is open/conflicting with a red live-smoke, so the drift survives merges.

## What Changes

- `qa-validate` validate job gains a merge-tree `make openspec-index-check` step after
  the PR-head `make openspec-check`, with a loud conflict/failure path and a tree restore.
- `tests/test_openspec_merge_tree_check.py` reads the real workflow and fails when any
  clause is dropped; §8 regression row added.

## Capabilities

### New Capabilities
- `openspec-merge-tree`: the pre-merge verification of generated files on the merge tree.

### Modified Capabilities
- (none)

## Impact

Workflow + rulebook + one test. No store data, no credentials, no agent CI dispatch.
