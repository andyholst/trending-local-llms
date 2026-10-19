# install-seam

## ADDED Requirements

### Requirement: A wrapped target never discards the seam's output

Every container wrapper that runs `make _setup` MUST keep its output visible (bare, or
redirected to stderr), so a failure inside the seam is reported with its reason instead
of as a bare non-zero exit.

#### Scenario: the wrappers are read from the Makefile

- **Given** the repository's `Makefile`
- **When** the guard collects every `sh -c "make _setup …"` wrapper
- **Then** it finds several, none contains `_setup >/dev/null`, and each keeps the output
- **Test:** tests/test_install_hermes_ci.py::test_no_wrapper_discards_the_seams_diagnosis

#### Scenario: the two targets that discarded it

- **Given** the `hermes-alias-check` and `hermes-smoke` recipes
- **When** the guard reads them
- **Then** each runs `make _setup` without discarding its output
- **Test:** tests/test_install_hermes_ci.py::test_no_wrapper_discards_the_seams_diagnosis
