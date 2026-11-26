# Proposal: openspec-archive-1763

Issue: #1763
PR: #1777

## Why

Three completed #1747 deliveries (`refresh-bot-pin-token`, `search-leg-sigpipe-classify`,
`test-image-qemu-handler`) were archived on this branch, but no OpenSpec change named #1763,
so `make openspec-archive-check PR=1777` refuses the PR as untracked work (rule 6f/#513).

## What Changes

- Archive the three completed changes with `PR: #1777` recorded and regenerate `OPENSPEC.md`.
- Declare this tracked change so the lifecycle gate can bind the issue to the archive work.

## Impact

- Capability: `openspec-lifecycle` — the archive sweep is tracked, not silent.
- No data, workflow, rulebook or host change.
