# Proposal: fleet-host-sync-config-version

Issue: #1389

## Why

`make fleet-host-sync-check` compares every lane `config.yaml` byte-for-byte with
`git show <fetched base>:agents/<lane>/config.yaml`. Hermes itself appends a runtime stamp,
`_config_version: <n>`, to every lane `config.yaml` on launch (`hermes_cli.config`). That key
appears nowhere in the repository (`grep -rn '_config_version' scripts/ tests/ agents/ AGENTS.md`
answers nothing), so a host that actually RUNS its lanes carries a 67-line file against a 66-line
base blob and the gate reds on all seven lanes after a single lane turn — measured on this host:
8 divergences (7 lanes plus the default profile). A divergence gate that cries wolf on exactly the
healthy hosts teaches the operator to re-provision reflexively, which can mask a genuinely stale
byte (issue #1389).

## What Changes

- `scripts/fleet_host_sync_check.py` drops ONE host-owned scalar — a line matching
  `_config_version: <value>` — from the host copy of a lane `config.yaml` before the byte
  compare. The tolerance is that key and that file only: a stale
  `model:` / `model_aliases:` / `fallback_providers:` byte still reds, and `SOUL.md` and the lane
  skill stay byte-exact.
- `tests/test_fleet_lifecycle.py::test_real_seam_tolerates_hermes_config_version` drives the REAL
  seam over a scratch home and proves both halves: a planted `_config_version` scalar is
  tolerated, a planted stale `model:` byte is refused naming `tll-implementer/config.yaml`, and a
  `_config_version` planted in `SOUL.md` is still refused.

## Impact

Host-side gate only. No make target, stage, workflow, contract, image or data change; the exits
stay 0 clean / 1 divergence (naming lane and file) / 2 undecidable. A host that runs its lanes now
stays green across a lane turn without a re-provision, while a genuinely stale lane byte is still
refused. RED-proved: with `origin/master`'s `scripts/fleet_host_sync_check.py` swapped into the
worktree the new guard answers `FAIL a planted _config_version scalar is tolerated` (1
divergence); with this change it is green and the whole module passes.

## Not covered

- The DEFAULT profile's owned blocks (`profile=default`) — that is #1297's seam, and the planner's
  dispatch for #1389 explicitly excludes it.
- Any other Hermes-written key: only `_config_version` is tolerated, so a second runtime stamp
  would red again and be filed separately.
- The `AGENTS.md` §8 row for `tests/test_fleet_lifecycle.py`: the rulebook is protected (rule 3c),
  so a headless leg records the owed row in `findings.md` instead of editing it.
