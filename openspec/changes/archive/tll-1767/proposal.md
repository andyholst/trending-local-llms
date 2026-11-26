# Proposal: tll-1767

Issue: #1767
PR: #1768

## Why

PR #1768 (branch fix/parallel-lane-rule-1767) implements issue #1767 — the owner's 2026-11-26 directive to allow up to three concurrent `tll-implementer` lanes, each on a distinct open issue, with a signed issue-thread claim and lease-checked pushes. The qa-validate `validate` job reds on the `OpenSpec lifecycle` step because no OpenSpec change on the PR names Issue: #1767. This change binds Issue: #1767 with PR: fix/parallel-lane-rule-1767 so the OpenSpec lifecycle step (openspec_binding_check, `openspec validate --changes`) accepts the PR head.

## What Changes

- Create openspec/changes/tll-1767/ with proposal.md (Issue: #1767, PR: fix/parallel-lane-rule-1767), tasks.md (one checked box) and a capability spec (tll-1767).
- Regenerate ROOT OPENSPEC.md from openspec/changes/** via `make openspec-index` (generated file; never hand-edited).
- git add the new change and the regenerated OPENSPEC.md, commit with a Conventional Commit, push to origin fix/parallel-lane-rule-1767. No merge, no master push.

## Impact

- Capability: `tll-1767` — the OpenSpec change binding Issue: #1767 with PR: fix/parallel-lane-rule-1767, satisfying the qa-validate OpenSpec lifecycle step.
- Additive only to the OpenSpec change tree and index; no data, contract, Makefile or workflow change.
- No closing keyword: issue #1767 stays open until the three parallel PRs (#1768, #1769, #1770) land.
