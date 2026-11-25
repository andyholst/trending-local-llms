## ADDED Requirements

### Requirement: The post-squash closure proof reads issues with a credential that can

`auto-merge`'s closure proof SHALL run under a token that carries the Issues scope, because `scripts/verify_closure.py` falls through to `gh issue view <n> --json state` whenever a `closingIssuesReferences` entry omits `state`, and the owner PAT declares no Issues scope. The squash-merge command, its owner-PAT credential and its `--match-head-commit` gate SHALL stay byte-identical.

#### Scenario: The proof runs beside the squash under the default token

- **Given** a green, non-draft, same-repo PR whose body closes an issue
- **When** `auto-merge` squashes it and runs the closure proof
- **Then** the proof step carries `GH_TOKEN: ${{ github.token }}` and the job declares `issues: read` and `pull-requests: read`
- **Test:** tests/test_verify_closure.py::test_the_merge_job_proves_closure_with_a_credential_that_can_read_issues

#### Scenario: A proof wired back to the owner PAT is refused

- **Given** the closure-proof step carrying `GH_TOKEN: ${{ secrets.FIXBOT_DISPATCH_TOKEN }}`
- **When** the wiring guard runs
- **Then** it fails naming the missing Issues scope, so a merge already landed can never redden the run again
- **Test:** tests/test_verify_closure.py::test_the_merge_job_proves_closure_with_a_credential_that_can_read_issues

#### Scenario: The squash path keeps its owner PAT

- **Given** the modified `auto-merge` job
- **When** the wiring guard inspects the squash step
- **Then** the squash still merges with the owner PAT and its `--squash --delete-branch --match-head-commit` flags are intact
- **Test:** tests/test_verify_closure.py::test_the_merge_job_proves_closure_with_a_credential_that_can_read_issues
