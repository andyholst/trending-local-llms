## ADDED Requirements

### Requirement: A fast offline pre-push guard refuses a push without an analysis

`file_findings.py --prepush` SHALL reuse the SAME resolution seam as the CI shape gate
(`analysis_path` → `slice_analysis_path` → `parse`) and SHALL refuse, with a non-zero exit
naming the expected file, when an implementation run has not written its per-issue analysis.
It SHALL NOT need a container or network, and SHALL NOT apply the CI gate's shape exemptions.

#### Scenario: A missing analysis is refused before push

- **Given** a tree with no `findings/1804.md` and no sibling slice
- **When** `--prepush --issue 1804` runs
- **Then** it exits non-zero naming `findings/1804.md` and prints no shape SKIP
- **Test:** tests/test_file_findings.py::test_prepush_guard_refuses_a_missing_analysis

#### Scenario: No issue bound is undecidable, never a pass

- **Given** a `--prepush` invocation with neither `--issue` nor a branch naming an issue
- **When** the guard resolves the analysis path
- **Then** it exits 2 and names the missing `ISSUE=<n>` remedy
- **Test:** tests/test_file_findings.py::test_prepush_guard_refuses_a_missing_analysis

#### Scenario: `- none` and one sibling slice are accepted

- **Given** a valid `- none` `findings/1804.md`, or exactly one `findings/1804-<slice>.md` when the canonical file is absent
- **When** `--prepush --issue 1804` runs
- **Then** it exits 0 and names the file it accepted
- **Test:** tests/test_file_findings.py::test_prepush_guard_accepts_none_and_one_slice

#### Scenario: Two sibling slices are a loud ambiguity

- **Given** two `findings/1804-*.md` slice files and no canonical file
- **When** `--prepush --issue 1804` runs
- **Then** it exits non-zero naming both files and never guesses one
- **Test:** tests/test_file_findings.py::test_prepush_guard_accepts_none_and_one_slice

### Requirement: The guard is reachable from the make target and the lane runs it

The guard SHALL be exposed through the existing CI-wired `findings-check-for-pr` target via
`PREPUSH=1 ISSUE=<n>` (no new make target, gate or registry entry), and the implementer skill
SHALL instruct host lanes to run it before any push. The plain CI invocation SHALL stay
host-side and byte-identical.

#### Scenario: Make forwards the flags without changing the plain call

- **Given** the `Makefile` `findings-check-for-pr` recipe
- **When** `PREPUSH=1` / `ISSUE=1804` are set, and when they are not
- **Then** the recipe adds `--prepush` / `--issue` only when set, keeps `$(PYTHON_RUN)` out, and CI's plain `make findings-check-for-pr` call is unchanged
- **Test:** tests/test_file_findings.py::test_prepush_guard_is_wired_to_the_lane_and_the_make_target

#### Scenario: The implementer lane runs the guard before push

- **Given** `agents/skills/issue-implement/SKILL.md`
- **When** a host lane prepares an implementation PR
- **Then** the skill directs it to run `make findings-check-for-pr PREPUSH=1 ISSUE=<n>` before any push
- **Test:** tests/test_file_findings.py::test_prepush_guard_is_wired_to_the_lane_and_the_make_target
