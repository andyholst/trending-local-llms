## ADDED Requirements

### Requirement: The §8 row names the fast offline pre-push findings guard

`AGENTS.md` §8 SHALL describe the fast offline pre-push guard for per-issue
findings analysis by extending the EXISTING `tests/test_file_findings.py`
(rule 6g, issue #172) row — never by adding a new row — with the three test
names `test_prepush_guard_refuses_a_missing_analysis`,
`test_prepush_guard_accepts_none_and_one_slice`, and
`test_prepush_guard_is_wired_to_the_lane_and_the_make_target`, each appearing
exactly once. The extension SHALL be the byte-exact text approved by owner
rule-3c sign-off (comment `7230162560`) from design `7219073743`, and SHALL NOT
touch the `#659` row at line 2484 or introduce mixed-shape / #1666 wording.

#### Scenario: The existing row is extended, not replaced by a new row

- **Given** `AGENTS.md` at base `3dfaa97b4259b0c9d4bf16d1f9669ecc679d35f7` with exactly two §8 rows naming `tests/test_file_findings.py` (line 2381 and line 2484)
- **When** the owner-signed replacement lands
- **Then** the tree diff is exactly one line changed at 2381, the module still has exactly two §8 rows, the row's pipe count is unchanged, and the line 2484 row is byte-identical
- **Test:** tests/test_owed_rows.py::test_a_landed_owed_row_is_reported_with_evidence

#### Scenario: The three pre-push guards are each named once

- **Given** the landed §8 row
- **When** the rulebook is read for the guard's reviewable home
- **Then** `test_prepush_guard_refuses_a_missing_analysis`, `test_prepush_guard_accepts_none_and_one_slice`, and `test_prepush_guard_is_wired_to_the_lane_and_the_make_target` each occur exactly once in `AGENTS.md`, and the owed-row ledger reports the missing-analysis needle as LANDED
- **Test:** tests/test_file_findings.py::test_prepush_guard_refuses_a_missing_analysis

#### Scenario: The refusal contract the row documents stays executable

- **Given** a host push of an implementation PR whose per-issue analysis file is missing
- **When** `make findings-check-for-pr PREPUSH=1 ISSUE=<n>` runs before the push
- **Then** it exits non-zero naming `findings/<issue>.md` with no shape SKIP; `- none` and exactly one sibling slice are accepted while two sibling slices are a loud ambiguity naming both
- **Test:** tests/test_file_findings.py::test_prepush_guard_accepts_none_and_one_slice

#### Scenario: The guard stays wired to the host target and the skill before push

- **Given** the host `findings-check-for-pr` target and the implementer skill
- **When** the wiring is checked
- **Then** `PREPUSH=1` adds `--prepush`, `ISSUE=` is forwarded, CI keeps the plain target, and the implementer skill runs the guard before any push
- **Test:** tests/test_file_findings.py::test_prepush_guard_is_wired_to_the_lane_and_the_make_target
