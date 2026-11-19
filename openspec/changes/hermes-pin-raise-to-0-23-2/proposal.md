# Raise the Hermes agent pin to the current release channel (0.23.2)

Issue: #1145
PR: #1146
Binding-exempt: none (implementation change)

## Why

`make hermes-pin-freshness` measures the drift on the current tree:

```
pin=0.23.1 channel=v0.23.2 DRIFT — the upstream release channel is strictly newer than the pinned agent version
```

`Makefile:120` (`HERMES_VERSION ?= 0.23.1`) and `Dockerfile:52`
(`ARG HERMES_VERSION="0.23.1"`) pin the agent version every fleet image bakes (rule 6k,
issue #218). The pinned build is reproducible but silently ages: the base image keeps
baking 0.23.1 while upstream released v0.23.2 on 2026-11-16, and the drift only surfaces
as a red alarm sweep (`queued-alarm.yml` → `make hermes-pin-freshness`) with no landed fix.

## What Changes

- Raise BOTH pins together — `HERMES_VERSION ?= 0.23.2` in the Makefile and
  `ARG HERMES_VERSION="0.23.2"` in the Dockerfile (never one pin alone, issue #218).
- Refresh the recorded channel fixture `tests/fixtures/hermes_releases_latest.json` to the
  real `v0.23.2` release payload recorded from the channel, so
  `test_recorded_channel_payload_is_compared_against_the_real_pins` proves `OK` against the
  pins it ships with (rule 6b: the contract change and its test move together).
- Land the ONE temp-Hermes-home teardown seam `tests/hermes_home.py` and use it wherever a test
  points Hermes at a temp home. Raising the pin to 0.23.2 made Hermes seed its own home
  (`cache/uv/**`, `installs/<hash>`, `cache/default-plugins.settled`) AFTER its CLI returned, so
  `tempfile.TemporaryDirectory`'s cleanup raced that pass and `make test` went RED in this PR's own
  qa-validate run 44537216542 (`tests/test_agent_skills.py`, every assertion green). Fixing the
  pipeline this change broke is part of this change (rule 6d), not a separate finding.

## Impact

- Capability: `hermes-pin-freshness` — the pinned version and the recorded channel payload
  agree, so the sweep is green instead of perpetually red.
- Capability: `hermes-temp-home-teardown` — a test's temp Hermes home is removed through one
  bounded-retry seam that fails loudly on a tree that never becomes removable, so the suite cannot
  go red on the agent's own bookkeeping.
- The Dockerfile edit changes the content hash, so the base image tag becomes
  `dockerfile-<new sha12>`: CI builds it (issue #1118 fallback) and the next refresh
  delivery publishes it multi-arch under the rule fixed by issue #1143 (PR #1144).
- No behaviour rule changes; no `AGENTS.md` section changes beyond the §8 regression-guard row this
  change owes (rule 6c: a pipeline bug fixed here gets its row in the same change — the guard
  `make hermes-pin-freshness` and its tests already existed, so the pin raise itself owed none).

## Not covered

- The publish act itself (`publish-agent-image.yml`, `workflow_dispatch` only, rule 6k's
  privileged publisher) — dispatching it is an owner act, not an agent act.
- Any other fleet lane's model choice (`agents/model_chain.json`, issue #1140) — untouched.
