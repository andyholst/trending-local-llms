## ADDED Requirements

### Requirement: A PR-blockage group never forms without a real failure signature

The PR-blockage pass SHALL spend only runs whose conclusion is `failure`, and SHALL skip any
member whose normalised signature is empty on both axes. A group therefore forms only when at
least `PR_BLOCK_MIN_PRS` open pull requests share a signature that carries a failing step name,
a `make` target or a quoted failing-region line — the error text rule 6r requires.

#### Scenario: Two cancelled open-PR runs file nothing

- **Given** two concluded `pull_request` runs whose conclusion is `cancelled`, each on a
  branch that is still an OPEN pull request inside the window
- **When** the PR-blockage candidate filter and the grouping run over them
- **Then** neither run is a candidate and no `pr-blockage` issue is filed for their branches
- **Test:** tests/test_pipeline_failure_issue.py::test_cancelled_and_empty_signature_runs_never_form_a_pr_blockage
- **Test:** tests/test_pipeline_failure_issue.py::test_two_cancelled_open_pr_runs_file_no_pr_blockage_end_to_end

#### Scenario: An empty-signature member cannot merge two branches into one blockage

- **Given** two members on two different open branches whose `shape` and `exact_shape` are both
  the empty digest `sha1("")[:12]` (no steps, no targets, no region lines)
- **When** `group_pr_blockages` groups the items
- **Then** no group is emitted for them, while a real shared signature on the same two branches
  still emits exactly one group naming both
- **Test:** tests/test_pipeline_failure_issue.py::test_cancelled_and_empty_signature_runs_never_form_a_pr_blockage

#### Scenario: End-to-end, the filer files no content-free blockage for cancelled runs

- **Given** a stubbed `gh` scene whose `pull_request` window holds two cancelled runs on the
  open branches `ci/a` and `ci/b`
- **When** the REAL filer runs with `--dry`
- **Then** its preview contains no `WOULD FILE pr-blockage` line, no issue body is written and no
  `trigger: "pull_request"` ledger row is appended
- **Test:** tests/test_pipeline_failure_issue.py::test_two_cancelled_open_pr_runs_file_no_pr_blockage_end_to_end
