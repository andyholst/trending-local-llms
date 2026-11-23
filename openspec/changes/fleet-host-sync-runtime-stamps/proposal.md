# Proposal: fleet-host-sync-runtime-stamps

Issue: #1401

## Why

`make fleet-host-sync-check BASE=origin/master` still reds on ONE lane: `tll-implementer/config.yaml`
carries `onboarding:\n  seen:\n    tool_progress_prompt: true`, a Hermes-written runtime stamp that
appears on 13 host profiles on this machine and nowhere in the repository. PR #1397 made the gate
tolerate ONLY `_config_version: <value>`, and its "Not covered" section named this exact residual:
*"Any other Hermes-written key: only `_config_version` is tolerated, so a second runtime stamp would
red again and be filed separately."* `onboarding.seen.tool_progress_prompt` is that second stamp, so
the gate cries wolf again on a healthy host — the same "teaches the operator to re-provision
reflexively" cost #1389 named.

## What Changes

- `scripts/fleet_host_sync_check.py` compares a lane `config.yaml`'s OWNED blocks (`model`,
  `model_aliases`, `fallback_providers`) against the fetched base blob through the ONE drift
  verdict (`agent_profile_provision.check_one`, the same seam #1297 drives for the default
  profile), instead of a byte compare minus one whitelisted key. ANY Hermes-written block —
  `_config_version`, `onboarding.seen`, the next stamp — is host runtime state and is tolerated.
- The teeth stay: a stale `model:` / `model_aliases:` / `fallback_providers:` byte still REDS,
  naming `tll-implementer/config.yaml`; `SOUL.md` and the lane skill stay byte-exact.
- `tests/test_fleet_lifecycle.py::test_real_seam_tolerates_hermes_runtime_stamps` drives the REAL
  seam over a scratch home and proves every tooth: `_config_version`, `onboarding.seen` and a
  NOVEL stamp are tolerated; a stale owned byte reds for each of the three blocks; the same blocks
  planted in `SOUL.md` are refused; a one-byte lane-skill drift is refused.

## Impact

Host-side gate only. No make target, stage, workflow, contract, image or data change; the exits
stay 0 clean / 1 divergence (naming lane and file) / 2 undecidable. A host that runs its lanes now
stays green across a lane turn AND across the next Hermes stamp, while a genuinely stale owned byte
is still refused. Measured on `asimov@mac`: `make fleet-host-sync-check BASE=origin/master` answers
`OK: base e5e52714…, 7 lane(s) …` on the real profile home, and the same seam run against a copy of
that home with `onboarding.seen` planted in `tll-implementer/config.yaml` also answers OK (0
divergences).

## Not covered

- The DEFAULT profile's owned blocks (`profile=default`) — that is #1297's seam, already in the gate.
- Any change to the lane SOULs, the lane skills, the model chain, a schedule or a workflow.
