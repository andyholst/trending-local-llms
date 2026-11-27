# implementer-lane-notes

## ADDED Requirements

### Requirement: the checked-in implementer skill carries the branch-rename and rebind pitfalls

The tracked mirror `agents/tll-implementer/skills/tll-implementer/SKILL.md` SHALL state that GitHub's branch-rename REST endpoint moves the ref without re-pointing an open PR's head (so deleting the old head closes the PR), and SHALL state that rebinding an existing PR to an issue other than the one encoded in its branch suffix requires a scope ruling. Both statements SHALL be asserted by the existing implementer-lane guard module.

#### Scenario: both forward notes survive in the checked-in mirror

- **Given** a tree whose implementer skill already declares the #1767 concurrent-lane contract
- **When** `test_skill_declares_the_branch_rename_and_rebind_pitfalls` reads the real tracked skill
- **Then** both pitfall needles are present and the assertion passes
- **Test:** `tests/test_parallel_implementer_lanes.py::test_skill_declares_the_branch_rename_and_rebind_pitfalls`

#### Scenario: the guard stays RED on the pre-note mirror

- **Given** the same skill text with only the two new paragraphs removed (the base revision)
- **When** the new test runs over that text
- **Then** it fails on both missing needles, proving the guard locks the landed notes
- **Test:** `tests/test_parallel_implementer_lanes.py::test_skill_declares_the_branch_rename_and_rebind_pitfalls`
