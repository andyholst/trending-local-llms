# code-review-scan

## ADDED Requirements

### Requirement: a refused `gh` read names the cost it actually had

When a `gh` read is refused, `code-review-scan` SHALL say what the refusal costs, and SHALL NOT
claim a check was skipped when it was not. A read whose refusal costs no check SHALL say so; a
read whose refusal does skip a check SHALL name that consequence.

#### Scenario: a refused secrets read claims no skipped check

- **GIVEN** a `gh` that refuses the `secret list` call the way the default token is refused
  (`HTTP 403`, measured on every production run)
- **WHEN** `defined_secrets` runs
- **THEN** it returns `None`, the message does NOT contain `SKIPPED this run`, and it states that
  no check is skipped by the refusal

- **Test:** `tests/test_code_review.py::test_a_refused_secrets_read_does_not_claim_a_skipped_check`

#### Scenario: a refused run-count read still names the check it skips

- **GIVEN** a `gh` that refuses the workflow-list call
- **WHEN** `workflow_run_counts` runs
- **THEN** it returns `None` and the message DOES contain `SKIPPED this run`, naming the real cost

- **Test:** `tests/test_code_review.py::test_a_refused_run_count_read_still_names_the_skipped_check`
