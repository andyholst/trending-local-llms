# refresh-sync Specification

## Purpose
TBD - created by archiving change refresh-fixture-generated-paths-1828. Update Purpose after archive.

## Requirements

### Requirement: The recorded channel fixture is a refresh-generated path

`refresh_base.GENERATED_PATHS` SHALL include `tests/fixtures/hermes_releases_latest.json`, the default output of `make hermes-pin-channel-record`, so `refresh-sync` accepts a tree dirty only in that fixture instead of refusing the whole refresh. The path SHALL be derived from the recorder's own Makefile seam in the guard, never re-typed as a second list.

#### Scenario: A tree dirty only in the recorded fixture is accepted

- **Given** a checkout on a base that has moved, with the recorded channel fixture rewritten by the pin recorder and no other foreign edit
- **When** `refresh_base.py sync` runs
- **Then** it exits 0 and reports `sync=reset` on the fetched tip instead of `REFUSED: CANNOT SYNC`
- **Test:** tests/test_refresh_base.py::test_sync_accepts_and_keeps_a_recorded_channel_fixture

### Requirement: A freshly recorded payload survives the reset

The recorded fixture SHALL also be in `refresh_base.KEEP_PATHS` so a pin raise lands its newly recorded payload in the refresh PR; the reset must not replace it with the base's copy.

#### Scenario: The recorded payload survives a sync onto a moved base

- **Given** the pin recorder wrote a new channel payload into the fixture before the base moved
- **When** sync resets the rest of the generated tree onto the fetched tip
- **Then** the fixture still holds the newly recorded payload
- **Test:** tests/test_refresh_base.py::test_sync_accepts_and_keeps_a_recorded_channel_fixture

### Requirement: The guard derives the path from the recorder seam

The test SHALL read the recorder's default `TO=` path from the real Makefile and assert it is present in both `GENERATED_PATHS` and `KEEP_PATHS`, so a future recorder output cannot drift out of the allow-list unnoticed. A foreign path remains refused.

#### Scenario: The recorder path is covered and a foreign path is still refused

- **Given** the shipped Makefile and the real `refresh_base` module
- **When** the generated-path guard runs
- **Then** the recorder's default fixture is in both tuples, and an unrelated `scripts/` edit is still refused by sync
- **Test:** tests/test_refresh_base.py::test_generated_paths_cover_the_hermes_pin_channel_recorder_fixture
