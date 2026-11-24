# Proposal: watch-s-marker-1620

Issue: #1620

## Why

#1265's design (section 5, Child 3) adds an `S:<issue>:<claim-id>:stale|released` detector
marker so a newly-stale claim reaches the fleet promptly. Today a stale claim is invisible
until a lane happens to re-read the thread, so two hosts can hold one issue or both stand down.

## What Changes

- Add `S:` to `MARKER_PREFIXES` in `scripts/watch_monitor.py`. It stays OUT of
  `bot_markers.REGISTRY`: it is a detector marker, not a bot window.
- Accept `S:` in the offline contract (`make watch-monitor CHECK=1`) and name it in the module
  docstring marker list.
- Guard both in `tests/test_watch_monitor.py::test_offline_check_mode`.
- Land the AGENTS.md §6w/§6j row naming the `<claim-id>` dedup key (rule-3c review-required).

## Impact

Purely additive: no recorded marker changes shape and no reader changes. A host that never
emits `S:` is unaffected.

## Not covered

- No CI dispatch, no merge, no master push, no new cron job, no collaborator grant.
