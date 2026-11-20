# hermes-pin-freshness

## ADDED Requirements

### Requirement: The shipped pins and the recorded channel payload name the SAME release

The `Makefile`'s `HERMES_VERSION ?=`, the `Dockerfile`'s `ARG HERMES_VERSION` and the recorded
payload `tests/fixtures/hermes_releases_latest.json` MUST name one and the same Hermes release
in the shipped tree. A pin raise that leaves the recorded payload quoting the older release — or
a payload refresh that runs ahead of the pins — is a defect in the change that did it, because
`make test` would then be locking a pair the repository no longer ships while the live
`make hermes-pin-freshness` gate is the only thing that notices (rule 6b: the pin move and its
test data move in the same change; rule 6d: one agreement, one guard).

#### Scenario: the pin, the ARG and the fixture agree byte-for-byte

- **Given** the repository's real `Makefile` pin, real `Dockerfile` `ARG HERMES_VERSION` and
  recorded `tests/fixtures/hermes_releases_latest.json` payload
- **When** the freshness suite compares the three spellings
- **Then** all three name the same version, and a planted tree where the fixture lags the pins
  is refused naming both spellings
- **Test:** `tests/test_hermes_pin_freshness.py::test_the_shipped_pins_and_the_recorded_payload_name_one_release`

#### Scenario: the refreshed payload stays green against the raised pins

- **Given** the raised pins (`0.23.3`) and the refreshed recorded payload (`v0.23.3`)
- **When** the freshness check runs with `--from-file` on that recorded payload
- **Then** it exits 0 printing `OK`, and it never calls `gh api`
- **Test:** `tests/test_hermes_pin_freshness.py::test_recorded_channel_payload_is_compared_against_the_real_pins`

#### Scenario: the image seam still refuses a CLI that is not the pin

- **Given** the raised `Makefile`/`Dockerfile` pins and the install seam's version assertion
- **When** the install-seam suite compares the pins and the baked version file
- **Then** both files spell `0.23.3`, the `Dockerfile` forwards it into the seam env, and a build
  whose `hermes --version` differs from the pin fails
- **Test:** `tests/test_install_hermes_ci.py::test_the_version_pin_has_one_definition_across_the_two_files`
