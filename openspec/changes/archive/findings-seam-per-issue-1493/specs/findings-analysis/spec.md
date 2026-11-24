## ADDED Requirements

### Requirement: The analysis artifact is resolved per issue

`scripts/file_findings.py` SHALL resolve the analysis file through ONE order: an
explicit `--path` wins; otherwise the per-issue file `findings/<issue>.md`, named from
`--issue` or from the issue the branch encodes (`scripts/pr_closure.implemented_issue`,
the ONE parser); with neither, the legacy root `findings.md` is the fallback so a caller
that predates this change still reads what it wrote. Two DIFFERENT issues SHALL resolve
to two different files, and a branch SHALL resolve to the same file as its `--issue`.

#### Scenario: Two issues resolve to two different files

- **Given** issues `1001` and `1002`
- **When** `analysis_path` resolves each
- **Then** the files differ and are named `1001.md` and `1002.md`
- **Test:** tests/test_findings_seam.py::test_each_issue_resolves_to_its_own_file

#### Scenario: A branch encodes the same issue as --issue

- **Given** the branch `ci/data-gap-1001-storage-x`
- **When** `analysis_path` resolves it
- **Then** the result equals `analysis_path(issue="1001")`
- **Test:** tests/test_findings_seam.py::test_each_issue_resolves_to_its_own_file

#### Scenario: An explicit path always wins

- **Given** `--path <file>` together with `--issue 1001`
- **When** the file is resolved
- **Then** the explicit file is used
- **Test:** tests/test_findings_seam.py::test_the_real_cli_checks_the_per_issue_file

#### Scenario: The real CLI checks the per-issue file and is loud when it is missing

- **Given** `findings/1001.md` containing `- none`, then removed
- **When** `main(["--check", "--issue", "1001"])` runs
- **Then** it exits 0 with `0 finding(s)`, then exits non-zero naming `1001.md`
- **Test:** tests/test_findings_seam.py::test_the_real_cli_checks_the_per_issue_file

### Requirement: Sibling branches touching different issues do not collide

Two sibling branches that record analyses for DIFFERENT issues SHALL merge cleanly in
either order, and the historical shared append point SHALL be proven to conflict, so
the guard can see the defect it prevents rather than asserting a property of a fixture.

#### Scenario: Two siblings merge cleanly in both orders

- **Given** a scratch repository whose branch A writes `findings/1001.md` and branch B
  writes `findings/1002.md`
- **When** A then B are merged, and separately B then A
- **Then** every merge exits 0 and both analyses survive with their own sections
- **Test:** tests/test_findings_seam.py::test_two_sibling_branches_touching_different_issues_do_not_collide

#### Scenario: The old root append point is the conflict

- **Given** the same two-branch shape, but both append a section to one tracked root
  `findings.md`
- **When** the second merges
- **Then** git exits non-zero and names `findings.md`
- **Test:** tests/test_findings_seam.py::test_the_old_shared_append_point_was_the_conflict

### Requirement: The shared root file is not a tracked append point

The repository SHALL NOT track a root `findings.md`; the historical sections SHALL stay
readable at `findings/history.md`; a stray root `findings.md` SHALL be gitignored; and
`make findings-check` SHALL forward `ISSUE=` so the bot paths and `REQUIRE_FINDINGS`
resolve the per-issue file.

#### Scenario: The tree and the gate agree on the seam

- **Given** `git ls-files`, `.gitignore` and the Makefile
- **When** they are read
- **Then** the root file is untracked, `findings/history.md` is tracked, the root path is
  ignored, and the plain gate passes `--issue "$(ISSUE)"`
- **Test:** tests/test_findings_seam.py::test_this_repository_is_on_the_per_issue_seam
