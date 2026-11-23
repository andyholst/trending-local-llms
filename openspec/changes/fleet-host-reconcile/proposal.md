# Proposal: fleet-host-reconcile

Issue: #1464

## Why

`make fleet-host-sync-check` refuses byte divergence but names no direction and offers no
remedy. Every `M:` wake therefore re-derives by hand whether a host's `SOUL.md`/skill is
BEHIND master (a pinned needle is missing) or FORWARD (extra experience notes), and the two
shapes demand opposite actions: a stale host must take master's bytes, a forward host must
NOT be wiped. A raw host copy into the tree would delete master's bytes and red
`tests/test_fleet_lifecycle.py`, so operators hand-diff four files every wake (#1456, #1464).

## What Changes

- New `scripts/fleet_host_reconcile.py`, importing the sync check's comparison inputs
  (`LANES`, `MIRROR_RELS`, `_blob`, `_git`) so exactly ONE definition of which files are
  compared against which base survives (rule 6d).
- A line-based verdict per divergent mirror: `FORWARD` (the host deleted nothing), `STALE`
  (the host is missing master's bytes) or `MIXED`.
- A LOSSLESS union: an ordered superset of BOTH inputs, so master's pinned needles are
  restored AND the host's forward notes survive; an exact duplicate contiguous run of >=2
  lines is dropped with a loud report (the #1456 hand-removed duplicate); a hard invariant
  refuses to write when a line would be lost.
- A timestamped `.bak-<UTC>` backup before ANY overwrite (never clobbering an existing one).
- One destination mechanism, two invocations: the HOST profile home by default (the §7b
  M:-wake refresh) or `DEST=<worktree>`'s `agents/<lane>/<rel>` (the reviewed delivery).
- `make fleet-host-reconcile` (host-side like `fleet-host-sync-check`), report-only by
  default, `WRITE=1` writes; `qa-validate`'s `validate` job runs the read-only half with
  `BASE=HEAD PROFILES_HOME=agents`; `ARCHITECTURE.md` target + script rows.

## Impact

Additive: `fleet_host_sync_check.py` gains only a `MIRROR_RELS` constant (its loop uses it)
and a new sibling module + target appear. No data format, contract, image or workflow trigger
changes; the CI step is deterministic and writes nothing. `config.yaml` stays with
`make agent-profile-provision` (#1198/#1204) — this seam never verdicts it.

## Not covered

- No change to the byte-compare gate's verdicts (it still refuses; this seam explains and
  lands the repair).
- No host profile is modified by CI: the write path is host-only by design.
- No new cron, no CI dispatch, no merge, no access grant.
- `AGENTS.md` §7b's M:-wake sentence and §8's guard row are review-required (rule 3c) and
  are declared as an owed row, not written by this headless leg.
