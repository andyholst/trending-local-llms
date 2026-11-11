# agent-image-publish

## ADDED Requirements

### Requirement: Only the registry's own "absent" wording means not published

A failed `docker manifest inspect` MUST be read as "the tag is absent" only when docker
says so (`manifest unknown`, `no such manifest`, `not found`); any other failure MUST fail
the run loudly instead of triggering a build.

#### Scenario: the registry cannot answer

- **Given** the tag IS published, and `manifest inspect` fails with `dial tcp …: i/o timeout`
- **When** `ensure-base` runs
- **Then** it exits non-zero, names docker's message, and performs no build
- **Test:** tests/test_ensure_image.py::test_a_registry_hiccup_is_a_loud_failure_not_a_rebuild

#### Scenario: the tag is genuinely absent

- **Given** the registry answers `manifest unknown` for this revision's tag
- **When** `ensure-base` runs
- **Then** it builds, exactly as before
- **Test:** tests/test_ensure_image.py::test_a_registry_hiccup_is_a_loud_failure_not_a_rebuild

### Requirement: The rebuild decision refuses to guess

When the registry cannot answer, `decide` MUST fail rather than print a rebuild decision,
because a wrong "built=yes" rebuilds and republishes the toolchain.

#### Scenario: decide meets a hiccup

- **Given** every tag published and `manifest inspect` failing with a network error
- **When** `decide --dow 1` runs
- **Then** it exits non-zero and prints no decision
- **Test:** tests/test_ensure_image.py::test_a_registry_hiccup_is_a_loud_failure_not_a_rebuild
