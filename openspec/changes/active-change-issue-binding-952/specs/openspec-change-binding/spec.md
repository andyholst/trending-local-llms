# openspec-change-binding

## ADDED Requirements

### Requirement: Every ACTIVE OpenSpec change binds its Issue before the record step can refuse

`make openspec-binding-check` MUST fail (exit 1) when any ACTIVE change under
`openspec/changes/` (everything except `archive/`) carries no `Issue:` line
naming `#<n>` in its `proposal.md` and declares no exemption, parsing the
binding through `openspec_index._refs` — the ONE proposal parser — so a plain
`Issue: #650` and a linked `**Issue:** [#715](https://…)` bind identically. An
ACTIVE change that implements no issue MUST state the declared exemption line
`Binding-exempt: <reason>`, which the check reports. The failure MUST name
each unbound change with its detail and the exact remedy. A tree the check
cannot read MUST be a loud exit 2, never a vacuous clean. The check MUST be a
prerequisite of `make openspec-check`, the gate qa-validate runs on every PR
and push, so an unbound change goes red while the implementing run can still
repair it.

#### Scenario: an unbound active change goes red with the exact remedy

- **Given** a planted tree with one ACTIVE change whose proposal has no Issue line
- **When** `scripts/openspec_binding_check.py` runs against it
- **Then** it exits 1, names the change, says no Issue line was found, and prints
  the `Issue: #<n>` / `Binding-exempt:` remedy
- **Test:** tests/test_openspec_binding.py::test_an_unbound_active_change_is_red

#### Scenario: both Issue spellings bind through the one parser

- **Given** a planted tree with `Issue: #650` and `**Issue:** [#715](https://…)` proposals
- **When** the check runs
- **Then** it exits 0 and counts both as bound
- **Test:** tests/test_openspec_binding.py::test_plain_and_link_issue_spellings_both_bind

#### Scenario: an Issue line naming no issue is unbound

- **Given** a planted ACTIVE change whose Issue line carries no `#<n>`
- **When** the check runs
- **Then** it exits 1 naming that detail
- **Test:** tests/test_openspec_binding.py::test_an_issue_line_naming_no_issue_is_unbound

#### Scenario: the declared keeper exemption is green and reported

- **Given** a planted ACTIVE change carrying `Binding-exempt: keeper …` and no Issue
- **When** the check runs
- **Then** it exits 0 and prints the exemption with its reason
- **Test:** tests/test_openspec_binding.py::test_the_declared_keeper_exemption_stays_green_and_is_reported

#### Scenario: prose about keeping never substitutes for the declaration

- **Given** a planted unbound ACTIVE change whose prose merely mentions keepers
- **When** the check runs
- **Then** it exits 1 — only the registered line exempts
- **Test:** tests/test_openspec_binding.py::test_silence_is_never_the_default_for_an_unbound_change

#### Scenario: archived history is out of scope

- **Given** a planted tree whose only change sits under `archive/` unbound
- **When** the check runs
- **Then** it exits 0 reporting zero active changes
- **Test:** tests/test_openspec_binding.py::test_archive_only_tree_is_green

#### Scenario: a change with no proposal is refused

- **Given** a planted ACTIVE change directory with no proposal.md
- **When** the check runs
- **Then** it exits 1 naming the missing proposal
- **Test:** tests/test_openspec_binding.py::test_a_change_without_a_proposal_is_red

#### Scenario: a tree the check cannot read is never clean

- **Given** a fixture with no changes directory at all
- **When** the check runs
- **Then** it exits 2 naming the unreadable tree
- **Test:** tests/test_openspec_binding.py::test_a_missing_tree_is_loud

#### Scenario: the shipped tree passes the gate it ships with

- **Given** the repository's real `openspec/changes/` tree
- **When** the check runs with no fixture seam
- **Then** it exits 0 with every active change bound
- **Test:** tests/test_openspec_binding.py::test_the_real_active_changes_are_all_bound

#### Scenario: the check is bundled into the merge gate, through the Makefile only

- **Given** the real Makefile and qa-validate workflow
- **When** the wiring is asserted
- **Then** `openspec-binding-check` is a prerequisite of `openspec-check`, its recipe
  runs the script via `$(PYTHON_RUN)`, it is `.PHONY`-registered, and no workflow
  calls it directly
- **Test:** tests/test_openspec_binding.py::test_the_binding_check_gates_the_merge_pipeline
