# agents-rulebook

## ADDED Requirements

### Requirement: rule 6h states the boundary

`AGENTS.md` rule 6h MUST state what `make architecture-check`
(`scripts/architecture_check.py`) proves and does not: PRESENCE of every make
target, workflow and script in the description, plus the two STRUCTURAL
cross-checks — every `--only` stage list of a Makefile target is a stage
`scripts/validate.py` registers, and every stage it registers is selected by
one such list; and §4's job tables/bullets name only real `jobs:` keys of the
workflow, name every real job, and every workflow has a §4 section. It MUST
also say the guard cannot read prose, so a sentence that is wrong about a real
target passes. `tests/test_architecture.py::test_validate_only_stage_lists_match_the_validator`,
`…::test_pipeline_job_names_match_the_workflow_job_keys` and
`…::test_doc_states_what_the_guard_does_not_prove` already lock the enforced
behaviour; the rulebook sentence must not promise more than they prove.

#### Scenario: the rulebook and the description agree about the same guard

- **Given** the #182 boundary landed in `scripts/architecture_check.py`'s
  docstring and `ARCHITECTURE.md` ("cannot read prose" + the two structural
  claims), and the three tests that lock it exist on master
- **When** a contributor reads AGENTS.md rule 6h to learn what "the guard
  keeps this file true" means
- **Then** the rule states that the guard proves presence plus the two
  structural claims and cannot read prose — never a prose-verifying promise
  the description does not make
- **Test:** tests/test_architecture.py::test_doc_states_what_the_guard_does_not_prove

#### Scenario: the §8 row names the checks that enforce rule 6h

- **Given** the `tests/test_architecture.py` row in AGENTS.md §8
- **When** a reader maps the guard to its regression tests
- **Then** the row names the two structural checks and their tests —
  `test_validate_only_stage_lists_match_the_validator`,
  `test_pipeline_job_names_match_the_workflow_job_keys`,
  `test_doc_states_what_the_guard_does_not_prove` — so the code that enforces
  the boundary is findable from the rule that claims it
- **Test:** tests/test_architecture.py::test_validate_only_stage_lists_match_the_validator
