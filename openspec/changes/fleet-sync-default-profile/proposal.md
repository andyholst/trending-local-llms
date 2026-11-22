# Proposal: fleet-sync-default-profile

Issue: #1297

## Why

`make fleet-host-sync-check BASE=origin/master` proves host/fleet agreement before a
lane takes work, but it compares only the SEVEN LANE homes and the `AGENTS.md`
lifecycle markers. The DEFAULT Hermes profile's owned blocks (`model`,
`model_aliases`, `fallback_providers` in `~/.hermes/config.yaml`) are invisible to
it — measured on this host at `3666bf84`: the sync check answered `OK` while
`make agent-profile-provision CHECK=1 PROFILE=default` named all three blocks STALE
on the retired `provider: custom` + `base_url`/`key_env` shape. A host can then run
for a week on a provider shape that answers HTTP 401 on inference while every gate
stays green — the "green in the repo, wrong on the machine" class.

## What Changes

- `scripts/fleet_host_sync_check.py` additionally renders the chain at the FETCHED
  BASE (`agents/model_chain.json` + the `Makefile` pins, read as base blobs into a
  scratch root — never the working tree) and compares the default profile's
  OWNED BLOCKS through `agent_profile_provision.check_one(..., whole_copy=False)`,
  the ONE drift verdict (rule 6d). A stale block FAILs naming `profile=default` and
  the drifted field(s).
- `tests/test_fleet_lifecycle.py` gains the RED-first guard: a synced default profile
  is green, a drifted `model:`/`fallback_providers:` block goes red naming the field.

## Impact

No data, contract, Makefile target, workflow or image change. The check reads one
more home and writes nothing; it still exits 2 on an undecidable base/home. A host
whose default profile is stale is now refused at the same gate that already refuses
a diverged lane.

## Not covered

- The other non-lane profile homes (a `PROFILE=<name>` merge home other than
  `default`) — they are not part of the fleet's fetched-base agreement.
- Re-provisioning the stale home: the gate reports, it never writes.
