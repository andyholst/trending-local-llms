# change-lifecycle

## MODIFIED Requirements

### Requirement: the guard fails an active change whose issue is closed with no recorded PR

When an ACTIVE change carries an `Issue:` ref but no `PR:` line, the repository
MUST query the referenced issue's state and, when the issue is CLOSED, treat the
change as a failure — its work ended (the completing PR merged it) yet no PR was
ever recorded, so a merged-and-forgotten change must be loud, never a vacuous
"nothing to assert" again (issue #518).

#### Scenario: an active change with a closed issue and no PR line

- **Given** an active change whose proposal names `Issue: #50` and no `PR:` line
- **When** the archive guard runs and GitHub answers that issue #50 is `closed`
- **Then** the guard exits 1, names the change and the issue, and tells the
  reader to run `make openspec-archive NAME=<change>`
- **Test:** tests/test_openspec_archive_check.py::test_a_closed_issue_without_a_recorded_pr_is_a_violation

#### Scenario: an active change with an open issue is in flight

- **Given** an active change whose proposal names `Issue: #60` and no `PR:` line
- **When** the archive guard runs and GitHub answers that issue #60 is `open`
- **Then** the guard exits 0 — the change is genuinely in flight, nothing to end
- **Test:** tests/test_openspec_archive_check.py::test_an_open_issue_without_a_pr_is_not_a_violation

#### Scenario: a recorded PR owns the change, whichever way its issue sits

- **Given** an active change that names a PR #7 (unmerged) AND an issue #50 (closed)
- **When** the archive guard runs
- **Then** it judges the change on the PR alone — the unmerged PR wins over the
  closed issue, because a PR was recorded and the primary prong owns it
- **Test:** tests/test_openspec_archive_check.py::test_a_change_with_a_pr_is_judged_on_the_pr_not_the_issue

#### Scenario: a change naming neither a PR nor an issue is still nothing to assert

- **Given** an active change whose proposal names no `PR:` and no `Issue:`
- **When** the archive guard runs
- **Then** it exits 0 with "nothing to assert" — there is no reference to judge
- **Test:** tests/test_openspec_archive_check.py::test_a_change_with_neither_pr_nor_issue_is_skipped

### Requirement: the completing PR's number is recorded on the change it completes, and the change is archived

Once a change's completing PR exists, the workflow that opened the PR MUST write
`PR: #<pr>` into every ACTIVE change whose proposal references `Issue: #<issue>`,
MOVE those changes to `openspec/changes/archive/`, and regenerate `OPENSPEC.md` —
so the change's reference is exposed to the guard and the change's lifecycle is
complete from that same PR on (rule 6f / issue #518).

#### Scenario: the recording writes the PR line, archives the change and updates the index

- **Given** an active change naming `Issue: #518` and an open PR number #523
- **When** `openspec-record-pr ISSUE=518 PR=523` runs
- **Then** the change sits under `openspec/changes/archive/` with `PR: #523` in
  its proposal, the index lists it as archived, and the recording names it
- **Test:** tests/test_openspec_record_pr.py::test_the_recording_writes_the_pr_line_archives_and_regenerates_the_index

#### Scenario: a recording that matched nothing is refused loudly

- **Given** an issue no active change references
- **When** `openspec-record-pr ISSUE=<unmatched> PR=<n>` runs
- **Then** it exits 2 naming the issue — a recording that silently matched
  nothing would leave the guard vacuous, which is the exact defect this fixes
- **Test:** tests/test_openspec_record_pr.py::record_refuses_when_no_change_names_the_issue

#### Scenario: an existing PR line is replaced, never duplicated

- **Given** an active change whose proposal already ends with `PR: #x`
- **When** `openspec-record-pr` records PR #y for the same issue
- **Then** the archived change carries exactly one `PR:` line, `#y`
- **Test:** tests/test_openspec_record_pr.py::record_replaces_an_existing_pr_line

### Requirement: the shared refs parser reads both header spellings

`scripts/openspec_index.py::_refs` MUST read both the bare `Issue: #170` /
`PR: #171` line and the bolded `**Issue:** [#170](url)` /
`**PR:** [#171](url)` form, so the guard and the index see every change's
reference — the old regex only matched the line-start form, hiding every bold
change's issue from the archive guard (issue #518).

#### Scenario: a bolded issue ref is parsed

- **Given** a proposal whose header is `**Issue:** [#498](https://github.com/…/498)`
- **When** `_refs` reads it
- **Then** it returns an issue ref the guard can read a number from (#498)
- **Test:** tests/test_openspec_index.py::test_bolded_refs_are_parsed
