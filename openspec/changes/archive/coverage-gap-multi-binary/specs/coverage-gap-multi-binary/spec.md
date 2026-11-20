# coverage-gap-multi-binary

## ADDED Requirements

### Requirement: the coverage-gap seam declares several external binaries in one line and probes them

`scripts/coverage_gap.py::external_binary_gap` accepts one binary name or a sequence of them. It
probes each with `shutil.which`, declares ONE line naming only the binaries the current identity
lacks, and returns `""` printing nothing when every binary is present.

WHEN a module declares a guard whose half needs two CLIs and this identity has only one
THEN one declared-gap line names the missing binary alone, and a later call whose binaries are
all present declares nothing.

#### Scenario: one line names only the missing CLI

- **Given** a real `external_binary_gap` driven in a subprocess whose `PATH` carries a stub `present-cli` and no `absent-cli`
- **When** the seam is called with `("present-cli", "absent-cli")`
- **Then** the returned and printed line names `absent-cli`, never `present-cli`, travels inside `GAP_PREFIX` with `BYPASS_PHRASE`, and uses the plural wording for two names and the singular for one
- **Test:** `tests/test_test_container_identity.py::test_the_seam_declares_several_external_binaries_in_one_line_and_probes_them` — real seam, real `shutil.which`

#### Scenario: every binary present declares nothing

- **Given** the same subprocess, calling the seam with only `("present-cli",)`
- **When** the seam probes
- **Then** it returns `""` and adds nothing to the captured stream
- **Test:** `tests/test_test_container_identity.py::test_the_seam_declares_several_external_binaries_in_one_line_and_probes_them` — real seam

#### Scenario: a module lets the seam probe instead of keeping its own `which`

- **Given** `tests/test_agent_skills.py`
- **When** the module is read and driven on a host with no `hermes`
- **Then** it calls the seam with no `shutil.which` of its own, stays green and declares the register half
- **Test:** `tests/test_test_container_identity.py::test_an_external_binary_gap_keeps_a_host_run_green_and_is_counted` — real module, stripped `PATH`
