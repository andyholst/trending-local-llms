## ADDED Requirements

### Requirement: The install pin names the agent version and the build proves it
`HERMES_VERSION` is part of the install pin with ONE default shared by the Makefile (`?=`) and the Dockerfile (`ARG`), and the install seam asserts after EVERY path that produces a CLI — including an already-present `hermes` — that `hermes --version` equals the pin. A mismatch fails the build, naming the pinned version and the version actually installed. When the version was verified, the seam writes it to `/opt/hermes-version.txt`, so the image built from a content-hash tag carries the version its tag can vouch for. An explicitly empty `HERMES_VERSION` records the installed version without asserting.

#### Scenario: a build that installs a different agent than the pin fails loudly
- **Given** the seam with a pin of `0.23.1` and a `hermes` on PATH answering `Hermes Agent v9.9.9 (…)`
- **When** the seam runs
- **Then** it exits non-zero and its output names both the pinned version and `9.9.9`
- **Test:** tests/test_install_hermes_ci.py::test_an_agent_that_is_not_the_pinned_version_fails_the_build

#### Scenario: the pinned version is verified and baked into the image
- **Given** the seam with the Makefile's pin and a `hermes` answering that version
- **When** the seam runs
- **Then** it exits 0 and the version file contains the pinned version
- **Test:** tests/test_install_hermes_ci.py::test_the_pinned_version_is_asserted_and_baked

#### Scenario: an explicit no-pin records without asserting
- **Given** the seam with `HERMES_VERSION` set to the empty string and any `hermes`
- **When** the seam runs
- **Then** it exits 0 and still writes the installed version to the version file
- **Test:** tests/test_install_hermes_ci.py::test_an_empty_pin_records_the_version_without_asserting

#### Scenario: the version pin has one definition across the two files
- **Given** the Makefile's `HERMES_VERSION ?=` and the Dockerfile's `ARG HERMES_VERSION=`
- **When** their defaults are compared
- **Then** they are the same value
- **Test:** tests/test_install_hermes_ci.py::test_the_version_pin_has_one_definition_across_the_two_files
