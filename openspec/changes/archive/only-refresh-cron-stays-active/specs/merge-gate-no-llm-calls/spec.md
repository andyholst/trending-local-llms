# merge-gate-no-llm-calls

## ADDED Requirements

### Requirement: the main CI pipeline gates merges on tests and validators only — never a real LLM call

`qa-validate.yml` (the pipeline whose `validate` + `live-smoke` green gate `auto-merge`)
runs unit tests, validators and deterministic checks ONLY. No real model call may gate a
merge: `make hermes-smoke` is removed from `live-smoke`, and no step of any qa-validate job
may invoke `hermes`, `hermes -z`, an agent target (`make implement-issue`,
`make review-issue*`, `make fix`, `scripts/fix_loop.sh`) or a search leg
(`make search-nvidia|metal|cpu|amd`). The deterministic bounded `make search-smoke` fetch
smoke (a Firecrawl scrape, no model) stays. Every real LLM call executes only through the
harness-image containers the Makefile launches (`DOCKER_RUN` recipes), in pipelines whose
`guard` admits the owner, a write collaborator, `github-actions[bot]` or a `schedule`
event (rule 6j) — never from a raw API call and never from an event any bot can author.

#### Scenario: no model call gates auto-merge

- **Given** `qa-validate.yml`'s `live-smoke` job
- **When** the suite reads its steps
- **Then** no step runs `make hermes-smoke`, `hermes`, or any agent/search target
- **Test:** tests/test_workflows.py::test_qa_validate

#### Scenario: the deterministic fetch smoke stays

- **Given** the same `live-smoke` job
- **When** the suite reads its steps
- **Then** the bounded `make search-smoke BACKEND=…` fetch smoke is still present
- **Test:** tests/test_workflows.py::test_qa_validate

#### Scenario: only refresh-bot may run scheduled LLM work

- **Given** every workflow's trigger surface
- **When** the suite scans for `on.schedule`
- **Then** only `refresh-bot.yml` has one (its search legs run the agent inside the
  harness image), and every other LLM-running pipeline starts only by admitted dispatch
- **Test:** tests/test_workflows.py::test_only_the_refresh_pipeline_carries_a_schedule
