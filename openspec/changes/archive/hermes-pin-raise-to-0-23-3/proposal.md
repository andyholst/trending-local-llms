# Raise the Hermes agent pin to the current release channel (0.23.3)

Issue: #1161
PR: #1162

## Why

`make hermes-pin-freshness REPO=andyholst/trending-local-llms` answers
`pin=0.23.2 channel=v0.23.3 DRIFT` — the upstream stable channel moved to
`v0.23.3` at 2026-11-20T00:34:38Z, 33 minutes before the first image build that
refused because of it. `Makefile:120` (`HERMES_VERSION ?= 0.23.2`) and
`Dockerfile:52` (`ARG HERMES_VERSION="0.23.2"`) name the agent version every
fleet image bakes (issue #218, rule 6k), and the seam refuses a build whose CLI
reports any other version. Measured consequence (qa-validate run 44651246625,
job `validate`, step "Prepare runner images", and the same failure in
`live-smoke`):

```
[install-hermes] Hermes Agent v0.23.3 (2026.9.24) · stable · local caafe5389ae5
[install-hermes] the installed agent is NOT the pinned version: pinned 0.23.2, installed 0.23.3
[install-hermes] the content-hash tag would vouch for 0.23.2; refuse to build a different agent (issue #218)
```

A stale pin is not a cosmetic lag: because the base image is the artifact every
`validate` and `live-smoke` job builds, a pin that lags the channel turns EVERY
open PR red at the image step, which is what happened repo-wide from
2026-11-20T00:34Z onward. The gate that names the drift already filed its own
issue (#1161); this change is the fix it asks for.

## What Changes

- Raise BOTH pins together in one commit (issue #218: never one pin alone):
  `HERMES_VERSION ?= 0.23.3` in the `Makefile`, `ARG HERMES_VERSION="0.23.3"` in
  the `Dockerfile`.
- Refresh `tests/fixtures/hermes_releases_latest.json` to the RECORDED
  `v0.23.3` release payload (taken from
  `gh api repos/NousResearch/hermes-agent/releases/latest`, not authored), so the
  recorded payload stays green against the shipped pins (rule 6b: the pin move
  and its test data move in the same change).
- Add one guard that the shipped pins and the recorded payload name the SAME
  release, so a future pin raise that forgets the fixture (or a fixture refresh
  that runs ahead of the pins) goes red in `make test`, not only at the live
  `hermes-pin-freshness` gate.

## Impact

- Affected specs: `hermes-pin-freshness` (the pin/fixture agreement).
- Affected code: `Makefile` (pin), `Dockerfile` (pin ARG),
  `tests/fixtures/hermes_releases_latest.json` (recorded payload),
  `tests/test_hermes_pin_freshness.py` (new agreement guard).
- Affected pipeline: every `qa-validate` `validate` / `live-smoke` image build
  (they bake the raised pin instead of refusing), and the `queued-alarm` sweep
  step that runs `make hermes-pin-freshness` (goes green, files nothing).

## Not covered

- Nothing in the agent's own configuration changes: the model/provider pins
  (`HERMES_ALIAS`, `model.aliases.*`, rule 6k) stay exactly as they are, and no
  credential is touched (rule 3e).
- It does NOT change what Hermes version the host agent runs — the pin is what
  the fleet images bake.
- It does NOT change `hermes-pin-freshness`'s verdict rule: a strictly newer
  channel is still a red verdict that files one drift issue (#1091), and an
  intentionally ahead pin is still reported, not red.
