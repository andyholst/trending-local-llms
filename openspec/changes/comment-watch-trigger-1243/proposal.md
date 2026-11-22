# Proposal: comment-watch-trigger-1243

Issue: #1243 (owner directive 2026-11-22)

## Why

Rule 6u says sync while CI runs, but new comments on issues/PRs were noticed only by
chance. The owner asked both machines to READ comments proactively and turn each new
one into a LOOK/reply, a new issue where work is requested, and an implementation.

## What Changes

- `scripts/comment_watch.py` + `make comment-watch`: read-only `gh api` report of
  comments newer than a local cursor, with an honest `--mark-read` that never rewinds.
- AGENTS.md rule 6w: READ the full thread, LOOK, reply, file new work, implement in a
  worktree PR; mark read only after the thread was answered; no CI dispatch / access grants.
- ARCHITECTURE.md target + script rows, §8 regression row, injected-OUTPUT suite.

## Capabilities

### New Capabilities
- `comment-trigger`: deterministic `gh`-backed detection of new issue/PR comments and
  the agent's READ/LOOK/reply/file/implement obligations.

### Modified Capabilities
- (none)

## Impact

One script, one Makefile target, rulebook + rulebook docs, one test. No GitHub writes
by the script, no credentials, no store data.
