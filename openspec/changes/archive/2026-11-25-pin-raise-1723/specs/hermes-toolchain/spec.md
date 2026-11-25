## ADDED Requirements

### Requirement: One Hermes agent version across the two pins and the recorded channel

The repository SHALL name the same Hermes agent release in the Makefile's `HERMES_VERSION ?=` default, the Dockerfile's `ARG HERMES_VERSION`, and the recorded channel fixture. A mismatch SHALL be refused before any image is baked (rules 6k/#218/#1161).

#### Scenario: The shipped pins and the recorded payload agree

- **Given** the shipped Makefile, Dockerfile and `tests/fixtures/hermes_releases_latest.json`
- **When** the shipped-tree agreement guard compares them through the gate's own parsers
- **Then** it reports no disagreement
- **Test:** tests/test_hermes_pin_freshness.py::test_the_shipped_pins_and_the_recorded_payload_name_one_release

#### Scenario: The two pin spellings keep one definition

- **Given** the Makefile and Dockerfile after the raise
- **When** the install pin guard compares the two version defaults
- **Then** both name `0.23.4` and the Dockerfile still forwards the pin into the build seam
- **Test:** tests/test_install_hermes_ci.py::test_the_version_pin_has_one_definition_across_the_two_files

### Requirement: The channel fixture is recorded through the one seam

A pin raise SHALL re-record the release-channel fixture through `make hermes-pin-channel-record`, writing the bytes the channel served — never an authored document — and a failed read SHALL leave the old fixture byte-identical.

#### Scenario: The recorded payload is compared against the real pins

- **Given** the recorded fixture and the raised pins
- **When** `make hermes-pin-freshness FROM_FILE=<fixture>` runs offline
- **Then** the gate answers `OK` and never calls `gh api`
- **Test:** tests/test_hermes_pin_freshness.py::test_recorded_channel_payload_is_compared_against_the_real_pins

#### Scenario: A failed channel read writes nothing

- **Given** a channel read that fails
- **When** the recorder runs
- **Then** it exits 2 and the tracked fixture is unchanged
- **Test:** tests/test_hermes_pin_freshness.py::test_a_failed_read_leaves_the_old_fixture_byte_identical
