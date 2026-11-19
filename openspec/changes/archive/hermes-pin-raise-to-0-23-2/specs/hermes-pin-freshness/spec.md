# hermes-pin-freshness

## ADDED Requirements

### Requirement: The recorded channel payload and the agent version pin agree

The Makefile's `HERMES_VERSION ?=` and the Dockerfile's `ARG HERMES_VERSION` MUST name the
same version (issue #218, rule 6k), and the recorded channel payload
`tests/fixtures/hermes_releases_latest.json` MUST record a release that the pinned version
is at least as new as, so that `make hermes-pin-freshness REPO=<repo>
FROM_FILE=tests/fixtures/hermes_releases_latest.json` exits green (`OK`, or `AHEAD` when a
pin bump intentionally runs ahead of the recorded payload). A red verdict from that command
is therefore always a REAL upstream move that still needs a pin raise (issue #1091), never a
stale fixture quoting a version the repo already passed.

Raising the pin is the fix for a drift: both pins move together in one reviewed change, and
the recorded payload is refreshed in the SAME change so the suite keeps proving the pair
(rule 6b).

#### Scenario: the recorded payload is green against the shipped pins

- **Given** the repository's real `Makefile`/`Dockerfile` pins and the recorded
  `tests/fixtures/hermes_releases_latest.json` payload
- **When** the freshness check runs with `--from-file` on that recorded payload
- **Then** it exits 0 printing `OK` (or `AHEAD`), and it never calls `gh api`
- **Test:** `tests/test_hermes_pin_freshness.py::test_recorded_channel_payload_is_compared_against_the_real_pins`

#### Scenario: the pin has ONE definition across the two files and the image asserts it

- **Given** the repository's `Makefile` and `Dockerfile`
- **When** the install-seam suite compares their `HERMES_VERSION` defaults and the baked
  version file
- **Then** both spell the same version, the Dockerfile forwards it into the seam env, and a
  build whose `hermes --version` differs from the pin fails
- **Test:** `tests/test_install_hermes_ci.py::test_the_version_pin_has_one_definition_across_the_two_files`

#### Scenario: a pin disagreement is refused before the channel is consulted

- **Given** a planted Makefile pin and a planted Dockerfile pin that differ
- **When** the freshness check runs
- **Then** it exits 2 naming both spellings and never consults the channel
- **Test:** `tests/test_hermes_pin_freshness.py::test_pin_disagreement_between_makefile_and_dockerfile_refuses_before_the_channel_is_read`

#### Scenario: a strictly newer channel is a red verdict that files ONE drift issue

- **Given** a planted channel payload strictly newer than the planted pins
- **When** the freshness check runs
- **Then** it exits 1 and files one `tech-debt` issue carrying the drift signature and the
  #218 "raise both pins together" remedy, and a re-run files nothing new
- **Test:** `tests/test_hermes_pin_freshness.py::test_channel_newer_goes_red_files_one_tech_debt_issue_naming_the_remedy`
