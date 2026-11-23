# Proposal: watch-marker-pr-identity-1355

Issue: #1355
PR: #1356

## Why

Issue #1284 added the trailing `:<pr>` field to the watcher's `R:` marker so a woken lane reads
that PR's own thread before acting. The field is derived from the run row's `pull_requests`, and
GitHub **clears** that association once the PR merges and its branch is deleted. Measured
2026-11-23: marker `R:45085274450:completed:failure:qa-validate` carried no PR field, while
`gh api …/actions/runs/45085274450` answers `event=pull_request`,
`head_branch=tech-debt-pr-health-agent-login-1349`, `pull_requests: []` — the branch maps to PR
#1350 (merged `203d7ac`). An earlier tick's marker for run `45075070900` DID carry `:1259`; between
the ticks the association was cleared. A lane waking on a merged PR's red head therefore sees a
bare run id and must re-derive the branch→PR mapping by hand, or miss the thread.

## What Changes

- `scripts/watch_monitor.py`: the caller-owned JSON state gains a `run_prs` map. A run's PR is
  recorded the first time the run is seen with a non-empty `pull_requests`, and reused on later
  ticks when the association has been cleared. `marker_state` stays pure; `pull_token` is
  unchanged. The marker's SHAPE never changes — a push run still emits the shorter form and a PR
  run keeps its trailing `:<pr>`.
- `tests/test_watch_monitor.py`: `test_r_marker_keeps_its_pr_after_the_merge_clears_the_association`
  drives the real pure diff with the post-merge `pull_requests: []` shape and asserts the PR
  field survives, the map is carried forward, and a push run keeps the shorter shape.
- `AGENTS.md` §8: the existing `tests/test_watch_monitor.py` row is EXTENDED (not duplicated) to
  name the merge-surviving PR identity. Rule 3c: **review-required** — declared blocked and filed
  as its own owed-row issue.
- `ARCHITECTURE.md` §6's `scripts/watch_monitor.py` row and §3's `watch-monitor` row updated;
  §10 regenerated.

## Impact

A red run on a merged PR's old head keeps its PR identity, so the woken lane reads the right
thread. No marker-shape change, no new target, no workflow change, no cron, no data-format change.
A host's existing state file without `run_prs` reads as an empty map (additive).

## Not covered

- No change to the marker grammar, the heartbeat, the claim-settle floor, or the C/M markers.
- No resolution of a run that was NEVER seen while its PR was open (the monitor's 5-minute
  cadence makes that a restart gap, not the measured case).
- No CI dispatch, no merge, no `master` push, no collaborator grant.
