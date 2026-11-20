## Tasks — #1163: a wired recorder for the release-channel fixture

### Seam

- [x] `scripts/hermes_pin_freshness.py::read_channel()` is the ONE read: `(payload, raw text)`, `from_file` or live `gh api`
- [x] `channel_tag()` keeps its contract by going through `read_channel()` (no second reader)
- [x] `--record PATH` writes the raw text the seam read (never an authored document), atomically (temp + rename)

### Refusals

- [x] A payload with no `tag_name` / no `published_at` / an unorderable tag is refused through the same `ChannelUnreadable`
- [x] A failed read (no gh, no network, non-JSON, no channel pin) exits 2 BEFORE any write — the old fixture byte-identical, no `.tmp` litter

### Target + wiring

- [x] `make hermes-pin-channel-record TO=<path>` + internal `_hermes-pin-channel-record` (Makefile-only, host-side)
- [x] `refresh-bot.yml` runs it beside `make engine-meta-capture`
- [x] The refresh PR's `git add` carries `tests/fixtures/hermes_releases_latest.json`

### Guard

- [x] `tests/test_hermes_pin_freshness.py::test_the_recorder_writes_the_live_payload_through_the_one_seam` — bytes are exactly what `gh` served; a payload the check refuses is refused
- [x] `tests/test_hermes_pin_freshness.py::test_a_failed_read_leaves_the_old_fixture_byte_identical` — exit 2, byte-identical, no litter, missing channel pin refused
- [x] `tests/test_hermes_pin_freshness.py::test_the_recorder_is_wired_into_the_refresh_pipeline_and_the_makefile` — Makefile-only + CI-wired, RED on a dropped step

### Rulebook

- [x] `AGENTS.md` §8's `tests/test_hermes_pin_freshness.py` row carries issue #1163 and names the recorder

### Verification

- [x] `make test` green
- [x] `make validate` green
- [x] `make lint` green
- [x] `make openspec-index` then `make openspec-check` green
- [x] `make architecture-check` green (after `make architecture-refresh` — the script docstring changed)

### Scope boundary

- No change to `make hermes-pin-freshness`'s verdicts, markers or wiring.
- No `--check` mode: landing the recorded payload in the refresh PR is the fix.
