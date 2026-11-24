# Proposal: land-implementer-rebase-conflict-note-1639

Issue: #1639

## Why

The #1363 lane recorded an `OPENSPEC.md` rebase-conflict lesson on its host skill only; the
in-tree mirror was left untouched per that dispatch, so the lesson had no delivery path. A
host re-provision then rewrote the host copy byte-equal to the base and deleted it, leaving
master and host both without the rule (measured on `asimov@mac` at base `45de6d49`).

## What Changes

- Land the note in `agents/tll-implementer/skills/tll-implementer/SKILL.md`, reconciled into
  its Pitfalls list: resolve the conflict with `python3 scripts/openspec_index.py --write`
  → `git add OPENSPEC.md` → `GIT_EDITOR=true git rebase --continue`, never `git commit`, then
  verify `git status -sb` names the branch, `openspec_index --check` is OK and
  `git ls-remote origin refs/heads/<branch>` matches the intended sha.
- Carry no host timestamp header, machine name or absolute path; keep the `#1363`/`PR #1609`
  reference.
- Pin the landing in `tests/test_fleet_lifecycle.py`: exactly once, inside the Pitfalls list,
  references intact, no host stamp.

## Impact

Documentation and its guard only. No script, contract, workflow, schedule, image or data-shape
change. `make fleet-host-sync-check BASE=origin/master` returns to 0 divergences once the host
re-syncs from the merged tree.

## Not covered

- The host-side re-provision itself: a host action outside this lane.
- Any other divergent mirror: this change touches only the tll-implementer skill mirror.
