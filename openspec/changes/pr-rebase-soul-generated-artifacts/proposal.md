# Proposal: pr-rebase-soul-generated-artifacts

Issue: #1361

## Why

The ruled `tll-pr-rebase` lane is the one repair path for a bot-owned branch whose
conflicts are confined to the generated artifacts (#1359), but its own contract has
no rule for that pair. `agents/tll-pr-rebase/SOUL.md`'s habitual-conflict list names
`data/*.json`, `README.md` and `openspec/changes/<slug>/` only, and its fallback is
"if the two sides genuinely contradict (a real redesign), stop and report". A stale
generated count line is not a redesign, so the lane stops-and-reports on exactly the
17 of 21 DIRTY PRs that conflict **only** on `OPENSPEC.md` / `ARCHITECTURE.md` §10 —
the PRs it exists to repair. The codebase already disagrees:
`scripts/pr_health.py::regenerate_index_on_rebased_tree` regenerates `OPENSPEC.md` on
every rebase it lands (#1049).

## What Changes

- Add `OPENSPEC.md` and `ARCHITECTURE.md` §10 to the lane's habitual-conflict list with
  the same rule `README.md` already carries: take the base revision of the generated
  file, regenerate (`make openspec-index`, `make architecture-refresh`), never
  hand-merge, and prove `git diff origin/master -- <file>` shows only the branch's own
  intended change.
- Add a guard (`tests/test_fleet_handover_protocol.py`) pinning the list, so a later
  edit cannot silently drop the generated pair again.

## Impact

Fleet-behaviour change only: one lane's SOUL. No data format, contract, image,
workflow or Makefile change. Hosts re-sync their `tll-pr-rebase` profile from the
merged base (`make fleet-host-sync-check BASE=origin/master`).

## Not covered

- No change to `pr-health`'s `CONFLICTING` exclusion — that is #1359's other branch
  and needs a ruling.
- No rebase of any PR by this change; it only makes the lane's contract match the
  codebase.
