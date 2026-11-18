## ADDED Requirements

### Requirement: a §4 job row may not claim a model or agent call the job never makes

ARCHITECTURE.md §4's `| Job | Does |` rows SHALL be read as behaviour claims, not
prose: when a row names a target that runs a real model or agent call — the
`check_secret_output.AGENT_TARGETS_TO_SCRUB` set plus `hermes-smoke` and `refresh`,
one list never re-spelled — that target MUST appear in the `run:` steps of that same
job in that workflow's YAML, or `make architecture-check` fails naming the workflow,
the job and the target. A denial (`no`, `not`, `never`, `without`, `removed`,
`dropped`, `no longer` beside the name) is history, not a claim, and never reds the
sentence that states it.

#### Scenario: the stale live-smoke row is refused

Given a `qa-validate`-shaped pipeline whose `live-smoke` job runs only fetch steps
and whose §4 row still lists `hermes-smoke` (the state `origin/master` held before
this change)
When `job_call_findings` runs over the tree
Then the finding names `` `ci.yml` ``, the job `` `live-smoke` `` and `` `hermes-smoke` ``,
and the same finding lands in `findings()` so `make architecture-check` exits red

- **Test:** tests/test_architecture.py::test_a_row_claiming_a_model_call_the_job_never_runs_is_reported

#### Scenario: a job that really calls the model is not flagged

Given the same fixture where the `live-smoke` job's steps do run `make hermes-smoke`
When the guard runs
Then it reports nothing — the rule is against a claim the tree denies, not against
model calls themselves

- **Test:** tests/test_architecture.py::test_a_row_naming_a_model_call_the_job_really_runs_is_green

#### Scenario: writing the correction does not red itself

Given a §4 row that says the job is fetch-only and that `hermes-smoke` was DROPPED
from it (the wording this change lands in `ARCHITECTURE.md` and `AGENTS.md` §6b)
When the guard runs
Then the denial is not read as a claim and the row is green

- **Test:** tests/test_architecture.py::test_saying_a_job_runs_NO_model_call_is_history_not_a_claim

#### Scenario: "what runs the agent" stays one list

Given `scripts/architecture_check.py` needs the set of model/agent targets
When `model_call_targets()` is read
Then it is `check_secret_output.AGENT_TARGETS_TO_SCRUB` as a subset plus the two live
Hermes legs, and no second copy of those target names exists in the check

- **Test:** tests/test_architecture.py::test_the_agent_target_list_is_one_list_not_a_second_copy

#### Scenario: the shipped description passes its own guard

Given the repository as shipped (12 pipelines, every §4 job row)
When `job_call_findings` runs over `ARCHITECTURE.md`
Then no row claims a model or agent call its job never runs — the corrected
`live-smoke` rows in `ARCHITECTURE.md` §4 and `AGENTS.md` §6b included

- **Test:** tests/test_architecture.py::test_the_shipped_documents_pass_the_model_call_guard
