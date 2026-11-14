## New Requirements

### Requirement: A "tool is missing" fixture sanitizes PATH instead of prepending to it

A test that asserts a product script fails loudly when an external tool is
absent MUST run that script with a PATH that contains ONLY the fixture bin
directory. Prepending the fixture directory to the developer's PATH is valid for
stub-resolution tests and invalid for missing-tool tests: on a host where the
tool is installed, a prepended PATH silently finds the real binary, the contract
goes unexercised, and the suite reports host-only failures that CI cannot see.

#### Scenario: missing-gh contract holds on a host that has gh installed

- **Test:** tests/test_openspec_archive_check.py::test_a_missing_gh_is_loud
- **Given** a host with a real `gh` on PATH (measured: `/opt/homebrew/bin/gh`) and an empty fixture bin directory
- **When** the archive-check script runs against an active change with PATH replaced by the empty fixture directory
- **Then** it exits 2 and names `gh` is not installed — on the host exactly as in the gh-less container image

#### Scenario: stub-resolution tests keep the developer PATH

- **Test:** tests/test_openspec_archive_check.py::test_a_merged_pr_left_an_active_change_behind
- **Given** a fixture bindir carrying the `gh` stub
- **When** any stub-driven test runs with the default prepend shape
- **Then** the stub answers every call and the real host `gh` is never consulted for the fixture PR numbers
