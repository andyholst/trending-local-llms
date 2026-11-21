# Proposal: profile-drift-check

Issue: #1204

## Why

The weekly free-tier refresh (issue #1195, merged PR #1205) moves the repo's chain, but nothing
re-provisions the HOST homes after a refresh merges — provisioning is an attended act. The defect
#1142 closed ("green in the repo, wrong on the machine") therefore reopens on a cadence, and no
alarm names the drift: a host silently runs a retired free model or misses a new one. This was
filed as the finding on PR #1205 (issue #1204): done when a drift check compares each host home
against the rendered chain and reports the stale homes loudly.

## What Changes

- `scripts/agent_profile_provision.py` gains `--check`: a READ-ONLY drift report over the same
  targets (`--lane`/`--all`/`--profile`, incl. `default`). A lane is a whole copy (the entire
  config must equal the render); a non-lane home is a merge (only the owned `model:`/
  `model_aliases:`/`fallback_providers:` blocks are compared — the home's other blocks are its
  own business). Every stale home/block is named (`[profile-drift] STALE …`), exit 1 on any
  drift, exit 0 `CLEAN` when all match, exit 2 for a missing home or unreadable chain. Writes
  NOTHING and needs NO credential — the host whose key is absent is exactly the host that needs
  the report.
- Makefile: `CHECK ?=` threaded into `PROVISION_ARGS` (`make agent-profile-provision CHECK=1
  ALL=1 PROFILE=…`); the public target's help names it.
- `tests/test_agent_profile_provision.py`: the stale-lane/stale-merge/clean-home report, the
  no-write/no-credential guarantees, green-after-provision, missing-home exit 2, and the CHECK=1
  wiring — each red on the pre-change seam (which refuses `--check` as an unrecognized argument).
- ARCHITECTURE.md rows + regenerated §10; AGENTS.md §8 provision row gains the drift-report
  contract (rule 3c attended sign-off, comment on #1204).

## Impact

- Capability: `fleet-model-chain` (the provision seam gains its read-only verdict).
- Additive: every existing provision behaviour, refusal and backup guarantee is unchanged; the
  credential pre-flight still guards every WRITE (the check precedes it and never writes).
- No new make target, pipeline job or image: the mode rides the existing seam and its tests
  (`make test` in qa-validate executes the real check end to end).

## Not covered

- Automatically re-provisioning the host after a refresh merge stays an attended act (the
  finding's other acceptable resolution — this change implements the loud drift report).
- The auxiliary blocks (`custom_providers[strata]`, moa) have their own drift check from issue
  #1198 (`make agent-aux-local-sync CHECK=1`); this mode compares only the provision-owned blocks.
