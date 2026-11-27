## ADDED Requirements

### Requirement: One explicit slice file satisfies the shape-aware gate

When the canonical `findings/<issue>.md` is absent, the shape-aware check SHALL
accept exactly one `findings/<issue>-*.md` file in its place. The canonical file
SHALL always take precedence, and a caller supplying `--path` SHALL never enter
the slice seam.

#### Scenario: A per-slice findings file is present

- **Given** an implementation-shaped branch closing issue 1767 and only `findings/1767-planner.md`
- **When** `make findings-check-for-pr` runs
- **Then** the gate exits 0 and reports `1767-planner.md`
- **Test:** tests/test_file_findings.py::test_the_shape_gate_accepts_a_slice_file_end_to_end

#### Scenario: The canonical findings file is present

- **Given** both `findings/1767.md` and a slice file exist
- **When** resolution runs
- **Then** the canonical file wins and the single-issue path is byte-identical
- **Test:** tests/test_file_findings.py::test_slice_resolution_covers_the_three_measured_shapes

#### Scenario: No findings file exists for the issue

- **Given** neither the canonical file nor any slice file exists
- **When** resolution runs
- **Then** the original missing-file failure names the canonical path and exits non-zero
- **Test:** tests/test_file_findings.py::test_the_shape_gate_accepts_a_slice_file_end_to_end

#### Scenario: Two slice files are present

- **Given** `findings/1767-planner.md` and `findings/1767-implementer.md` in one tree
- **When** resolution runs
- **Then** it fails loudly naming both candidates instead of guessing
- **Test:** tests/test_file_findings.py::test_slice_resolution_covers_the_three_measured_shapes
