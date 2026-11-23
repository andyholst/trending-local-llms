# Proposal: dispatch-guard-claims-1458

Issue: #1458

## Why

Measured on master `9d5e38d5`: three `agents/tll-planner/skills/tll-planner/SKILL.md`
bullets appear twice verbatim because PR #1448 merged a concurrent edit as `0df63311`;
`make fleet-host-sync-check` reds on 3 lanes; and four of the last six PRs (#1418, #1432,
#1445/#1449, #1448) edited the SAME two `agents/<lane>/skills/<lane>/SKILL.md` mirrors at
once, so #1434 rebased onto SIX successive master tips. `scripts/dispatch_guard.py`
(#1416/#1428) bounds lane COUNT, not WHICH FILES a lane will touch, so two dispatches can
claim the same mirror and race.

## What Changes

- Extend `scripts/dispatch_guard.py`, do not rewrite it: the caller-owned registry's per-lane
  rows gain a `claims` list of repo-relative paths; `--claim <path>` (repeatable, or
  `CLAIMS="p1 p2"`) adds an overlap check that refuses when another **ACTIVE** lane already
  claims the same path or a containing directory, naming the holding lane. A FINISHED
  lane's claims never block.
- Keep every existing refusal intact: CLOSED issue, MERGED bound PR, `ACTIVE_LANE_CEILING`,
  and the in-repo registry refusal. An absolute/`..` claim is refused as not repo-relative.
- `make dispatch-check ISSUE=<n> CLAIMS="<p1> <p2>"` forwards the claims; GNU make rejects a
  literal `--claim` after the target, so `CLAIMS=` is the make-side spelling. With NO claim
  the target behaves EXACTLY as it does today — the registry's new key is not even read.
- Add fixture tests to `tests/test_dispatch_guard.py`: allow on no overlap, refuse on an
  ACTIVE overlap naming the lane, allow on a FINISHED overlap, refuse an in-repo
  (absolute) claim, plus the CLI/make seam. Offline, no network, no credential values.

## Impact

Additive and read-only: no schema, contract, workflow schedule, data shape or CI gate
changes. The guard spawns no lane, writes no state, reads no credential value, and merges
nothing. The caller still owns the registry's lifecycle; a pre-#1458 registry without the
new key stays valid and unchanged in behaviour until a caller passes a claim.

## Not covered

- No registry WRITER and no planner-side rollout: the fleet owner creates and updates the
  external file.
- No change to the planner's delegation rules, the watch monitor, or any protected file
  (`agents/*/SOUL.md`, `AGENTS.md` §7b/§8).
- No GitHub API write, no label change, no issue comment by the guard itself.
