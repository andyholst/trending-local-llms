## ADDED Requirements

### Requirement: A failing rebase seam prints its own output

The qa-validate `auto-merge-rebase` step SHALL capture the seam's exit status beside the
command instead of letting `set -euo pipefail` kill the assignment, SHALL always echo the
seam's captured output, and SHALL then exit with the seam's own status. errexit SHALL NOT be
disabled to achieve this.

#### Scenario: The seam fails after a landed rebase

- **Given** the shipped `auto-merge-rebase` step shell and a `make auto-merge-rebase` that exits non-zero with a diagnosis on stdout
- **When** the step runs under `set -euo pipefail`
- **Then** the diagnosis text appears in the step output and the step exits with the seam's status
- **Test:** tests/test_auto_merge_rebase.py::test_a_failing_rebase_seam_shows_its_own_output_in_the_job_log

#### Scenario: The seam succeeds

- **Given** the same step shell and a seam that exits zero printing `rebased=true`
- **When** the step runs
- **Then** it still prints the seam output and publishes the allowlisted `rebased=` key
- **Test:** tests/test_auto_merge_rebase.py::test_a_failing_rebase_seam_shows_its_own_output_in_the_job_log

### Requirement: The push identity is asserted from GitHub's own run record

For every rebase push that lands, the seam SHALL read the actor and triggering actor GitHub
recorded for the run that push created, SHALL classify them into `checkout-credential` or
`owner-pat`, and SHALL print the proven class beside the intended one with a
`push_identity_proved=` verdict. An unreadable identity SHALL be reported, never guessed.

#### Scenario: The recorded actor selects the label

- **Given** GitHub's own run record as `actor.login` and `actor.type`
- **When** the classifier runs
- **Then** a Bot actor is `checkout-credential`, a User of this repository is `owner-pat`, and an unknown or absent actor is `unknown`
- **Test:** tests/test_auto_merge_rebase.py::test_the_recorded_actor_selects_the_push_identity_label

#### Scenario: The read refuses a silent guess

- **Given** the real identity reader and a `gh api` that fails or answers no actor
- **When** it runs
- **Then** it raises loudly and returns no label
- **Test:** tests/test_auto_merge_rebase.py::test_the_identity_read_uses_githubs_own_record_and_never_guesses

#### Scenario: The PR #1631 shape is proved, not assumed

- **Given** a rebase whose local intent is `owner-pat` while GitHub records `github-actions[bot]` and the run carries zero jobs
- **When** the seam reports the outcome
- **Then** the output names the actor and triggering actor, prints `push_identity=checkout-credential`, `push_identity_intended=owner-pat`, `push_identity_proved=false`, and still refuses `rebased=true`
- **Test:** tests/test_auto_merge_rebase.py::test_the_seam_proves_the_pushed_identity_from_githubs_own_run
