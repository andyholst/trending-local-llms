# rulebook

## ADDED Requirements

### Requirement: The §8 guard row names the analysis-seam suite

`AGENTS.md` §8 MUST carry exactly one row naming `tests/test_findings_seam.py` — the
per-issue analysis-file seam guard that shipped in #1493 (PR #1592) — beside its five
guard functions, the rules it serves and the defect it prevents, so the sibling-collision
guarantee is discoverable rather than silently unguarded. The row's text SHALL match the
reviewer-approved landing text on #1602 byte-for-byte.

#### Scenario: the row exists in §8

- **Given** `AGENTS.md` at the landing head
- **When** the guard reads the first §8 line naming `tests/test_findings_seam.py`
- **Then** the row exists and also names
  `test_two_sibling_branches_touching_different_issues_do_not_collide`,
  `test_the_old_shared_append_point_was_the_conflict`, `#1493` and `#1602`
- **Test:** tests/test_findings_seam.py::test_rulebook_section_8_carries_the_analysis_seam_row

#### Scenario: deleting the row turns the guard red

- **Given** an `AGENTS.md` whose §8 no longer carries that row
- **When** the guard runs
- **Then** it fails loudly with `AGENTS.md §8 dropped the analysis-seam guard row` and the
  module exits 1
- **Test:** tests/test_findings_seam.py::test_rulebook_section_8_carries_the_analysis_seam_row

#### Scenario: the owed-row ledger reports the row LANDED

- **Given** the landing tree
- **When** `python3 scripts/owed_rows_check.py --repo andyholst/trending-local-llms` runs
- **Then** it reports `#1602 section=8 needle='tests/test_findings_seam.py' LANDED
  AGENTS.md:<line>`; on the base alone it reports `OUTSTANDING`
- **Test:** tests/test_findings_seam.py::test_rulebook_section_8_carries_the_analysis_seam_row
