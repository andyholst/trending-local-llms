# hermes-pin-channel-record

## ADDED Requirements

### Requirement: the recorded channel payload is written through the ONE read seam

`scripts/hermes_pin_freshness.py` exposes `read_channel(from_file, channel_repo)` returning
`(payload, raw text)`. `channel_tag()` keeps its public contract by going through it, and the
`--record PATH` mode writes the RAW text the seam read — never an authored document and
never a re-serialisation — so the freshness check and the recorder cannot disagree about
what the channel said. A payload with no `tag_name`, no `published_at`, or a tag that is not
a version is refused through the same `ChannelUnreadable` the check uses.

WHEN the recorder writes a payload
THEN the bytes on disk are exactly what the channel served,
AND a payload the check would refuse is refused by the recorder too,
AND the write is atomic (temp file + rename), leaving no `.tmp` litter.

#### Scenario: the recorder writes exactly what `gh` served

- **Given** a stub `gh` on PATH answering `repos/<planted-channel>/releases/latest` with a planted payload
- **When** `make hermes-pin-channel-record TO=<path>` runs with the Makefile's channel pin
- **Then** the file's bytes equal the stub's payload plus one newline, it carries the channel's `tag_name` and `published_at`, and stdout names both
- **Test:** `tests/test_hermes_pin_freshness.py::test_the_recorder_writes_the_live_payload_through_the_one_seam` — real seam, real bytes

#### Scenario: the recorder refuses what the check refuses

- **Given** a payload carrying no `tag_name`
- **When** the recorder runs
- **Then** it exits 2 naming ``no `tag_name` `` and the target file is unchanged
- **Test:** `tests/test_hermes_pin_freshness.py::test_the_recorder_writes_the_live_payload_through_the_one_seam` — the ONE seam

### Requirement: a failed read leaves the old fixture byte-identical

`--record` reads the payload FIRST and writes only after a successful read. When `gh` is
missing, the network fails, the payload is not JSON, or the Makefile carries no
`HERMES_CHANNEL_REPO ?=` pin, the recorder exits 2 naming the cause and states that nothing
was written; the previous fixture is byte-identical and no temp file remains.

WHEN the channel cannot be read
THEN the recorder exits 2 BEFORE any write,
AND the old fixture is byte-identical,
AND stderr says the read failed and that nothing was written.

#### Scenario: an unreadable channel writes nothing

- **Given** a stub `gh` that refuses `gh api` (the unreadable-channel state), and a target file holding a previous payload
- **When** the recorder runs
- **Then** it exits 2, stderr names the failed read and that nothing was written, the file is byte-identical, and no `.tmp` file remains
- **Test:** `tests/test_hermes_pin_freshness.py::test_a_failed_read_leaves_the_old_fixture_byte_identical`

#### Scenario: a Makefile with no channel pin refuses before gh is consulted

- **Given** a planted Makefile carrying `HERMES_VERSION ?=` but no `HERMES_CHANNEL_REPO ?=`
- **When** the recorder runs against it
- **Then** it exits 2 naming `HERMES_CHANNEL_REPO` and the target file is still byte-identical
- **Test:** `tests/test_hermes_pin_freshness.py::test_a_failed_read_leaves_the_old_fixture_byte_identical`

### Requirement: the recorder is Makefile-only and a CI job runs it

`make hermes-pin-channel-record TO=<path>` (internal `_hermes-pin-channel-record`) is the
ONLY path to the recorder — no workflow names `scripts/hermes_pin_freshness.py` directly
(rule 6m) — and `refresh-bot.yml` runs it beside `make engine-meta-capture`, with the
refresh PR's `git add` carrying `tests/fixtures/hermes_releases_latest.json` so the
recorded payload lands in a reviewed PR.

WHEN the Makefile and `refresh-bot.yml` are read
THEN the target exists and expands the Makefile's channel pin,
AND the workflow runs `make hermes-pin-channel-record TO=tests/fixtures/hermes_releases_latest.json`,
AND the PR's `git add` carries that fixture.

#### Scenario: the target is wired and a dropped step is refused

- **Given** the Makefile and `refresh-bot.yml`
- **When** the test reads them and `make -n` renders the recipe
- **Then** the target and internal recipe exist, `make -n` runs the script with `--record` and the channel pin, a missing `TO` is refused, and the workflow's `git add` line carries the fixture — while removing the step from the workflow is detected
- **Test:** `tests/test_hermes_pin_freshness.py::test_the_recorder_is_wired_into_the_refresh_pipeline_and_the_makefile`
