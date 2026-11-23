# Proposal: watch-marker-pr-first-seen

Issue: #1364
PR: #1366

## Why

Issue #1355 added the caller-owned `run_prs` map so a run keeps its PR identity after GitHub
clears `pull_requests` on merge. The map only records a run that was **seen while its PR was
open**, and its "Not covered" section said so explicitly. Measured 2026-11-23: the marker
`R:45116060775:completed:failure:qa-validate` carried **no PR field** for PR #1362's old head,
because the detector's first sight of that run was after the PR merged (`2d5b1be`, 05:34:20Z)
and the branch was deleted; this host's state records `run_prs: {}`. Auto-merge lands a PR
minutes after the run concludes, so "first sight is post-merge" is the common shape, not a
restart gap. A woken lane then sees a bare run id and must re-derive branch→PR by hand — the
exact second lookup the protocol forbids — or miss the thread.

## What Changes

- `scripts/watch_monitor.py`: a PR run whose live `pull_requests` is empty and whose
  `head_branch` is resolvable gets its association back **before** the diff.
  `resolve_branch_prs` (network half) asks `gh pr list --state all --head <branch>`, which
  keeps answering after the merge and the branch deletion; `inject_run_prs` (pure half) is the
  only place a resolved number enters a run row, so `marker_state` stays pure. The per-tick
  budget `PR_RESOLVE_MAX` bounds the request count. An ambiguous, empty or unreadable branch
  resolves to nothing — never a guess.
- `tests/test_watch_monitor.py`: `test_r_marker_resolves_a_pr_first_seen_after_the_merge`
  drives the pure chain with the measured first-sight shape and asserts the marker names the PR
  and the map records it, plus the push / unresolved / live-association negatives;
  `test_branch_resolution_is_capped_and_never_guesses` drives the real request through a stub
  `gh` on PATH (the external CLI, rule 6m) and asserts unique-only resolution and the budget.
- `ARCHITECTURE.md` §6's `scripts/watch_monitor.py` row updated; §10 regenerated.

## Impact

A red run on a merged PR's head keeps its PR identity even when first seen post-merge, so the
woken lane reads the right thread. No marker-shape change, no new target, no workflow change,
no cron, no data-format change, no contract change. A host's existing state file is untouched
(the map is additive); the resolution only adds `gh pr list` calls on ticks that have an
unresolved PR run.

## Not covered

- No change to the marker grammar, the heartbeat, the claim-settle floor, or the C/M markers.
- No resolution from a source other than `head_branch` (a run with no `head_branch` keeps the
  shorter shape).
- No caching of resolutions across ticks beyond the existing `run_prs` map.
- No CI dispatch, no merge, no `master` push, no collaborator grant.
