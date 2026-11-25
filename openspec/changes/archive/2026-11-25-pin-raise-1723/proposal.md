# Proposal: pin-raise-1723

Issue: #1723
PR: #1725

## Why

`make hermes-pin-freshness` filed #1723: the repository pins the Hermes agent to `0.23.3` in both `Makefile` and `Dockerfile`, while the upstream stable release channel now serves `v0.23.4`. A pinned build is reproducible but silently ages — every fleet image keeps baking a version the channel has passed, and the drift only surfaced at the next image dispatch (`refresh-bot` run 45585404150's `pin-freshness` job failed). Rule 6k requires both pin spellings to move together as one explicit, reviewable change; #218 forbids raising only one.

## What Changes

- Raise `HERMES_VERSION ?=` in `Makefile` from `0.23.3` to `0.23.4`.
- Raise `ARG HERMES_VERSION` in `Dockerfile` from `0.23.3` to `0.23.4`.
- Re-record `tests/fixtures/hermes_releases_latest.json` through `make hermes-pin-channel-record` (the ONE recorder seam, #1163) so the offline fixture carries the live `v0.23.4` payload the gate actually reads.
- Add this tracked change; no code, contract, workflow, target or rulebook change.

## Impact

Both pins and the recorded fixture must name one release or `tests/test_hermes_pin_freshness.py::test_the_shipped_pins_and_the_recorded_payload_name_one_release` fails. No data format, image wiring, schedule or CI dispatch changes. The next image build bakes `0.23.4`.

## Not covered

- No rulebook edit, no new guard, no merge, no master push, no collaborator grant. The arm64 image build failure (missing `libX11.so.6` for `cua-driver`) is tracked separately in #1724 and is not touched here.
