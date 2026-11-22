# auto-merge-head-guard

## ADDED Requirements

### Requirement: the squash refuses a head that moved after validation

`qa-validate`'s `auto-merge` job MUST re-read the PR's `headRefOid` in its own
step immediately before the squash and compare it with the head SHA from the
`pull_request` event that was validated. The verdict MUST be `same` only when
both SHAs are present and equal (case-insensitively); a missing SHA is
`unreadable`, never folded into `same`. Only a proved `same` head MAY report
`head_moved=false`; a `moved` OR `unreadable` head MUST fail closed with
`head_moved=true` naming both SHAs, and the squash step MUST NOT run for it.

#### Scenario: an identical head proceeds

- **Given** the event head `c9291dac…` and the PR's current head `c9291dac…`
- **When** the head-check seam compares them
- **Then** it reports `head_moved=false` and the squash step's `if:` allows the merge
- **Test:** `tests/test_auto_merge_head_check.py::test_the_real_script_reads_the_head_through_the_field_contract`

#### Scenario: a moved head refuses and is re-validated by the fresh run

- **Given** the event head `2222…` and a current head `1111…`
- **When** the head-check seam compares them
- **Then** it reports `head_moved=true`, names both SHAs in the refusal, and the
  squash step's `if:` skips the merge so the new head's own `pull_request` run
  re-validates and lands it
- **Test:** `tests/test_auto_merge_head_check.py::test_a_moved_head_refuses_with_both_shas_and_skips_the_merge`

#### Scenario: an unreadable head refuses instead of a silent merge

- **Given** an empty event SHA or an empty current SHA
- **When** the head-check seam compares them
- **Then** the verdict is `unreadable` and it reports `head_moved=true` (never `false`),
  naming the refusal
- **Test:** `tests/test_auto_merge_head_check.py::test_an_unreadable_head_refuses_instead_of_a_silent_merge`

### Requirement: the head-read is a field-contract read through the Makefile

The head-check step MUST reach the decision through `make auto-merge-head-check`
(rule 6m), using the default `github.token` for a read-only `gh pr view --json
headRefOid` request validated by the ONE `gh --json` field contract (rule 6d).
A failed gh read MUST be exit 2 with a `READ FAILED` line, never a silent
`head_moved=false` that would merge an unproven head.

#### Scenario: a failed GitHub read is loud

- **Given** a `gh` that exits non-zero
- **When** the head-check script reads the PR head
- **Then** it exits 2 with `READ FAILED` and prints no `head_moved=false`
- **Test:** `tests/test_auto_merge_head_check.py::test_a_failed_gh_read_is_exit_2_not_a_silent_clean`

#### Scenario: the workflow gates the squash on the head-check output

- **Given** `.github/workflows/qa-validate.yml`
- **When** the `auto-merge` job's steps are read
- **Then** a `head-check` step calling `make auto-merge-head-check` with
  `EVENT_HEAD: ${{ github.event.pull_request.head.sha }}` and the default token
  precedes the squash, whose `if:` requires `steps.head-check.outputs.moved != 'true'`
- **Test:** `tests/test_auto_merge_head_check.py::test_the_workflow_guards_the_squash_on_a_moved_head`
