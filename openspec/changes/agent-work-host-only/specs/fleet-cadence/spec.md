## ADDED Requirements

### Requirement: an agent session never dispatches a pipeline and does its bot work on the host

A Hermes/agent session MUST NOT start any repository pipeline — no `gh workflow run`, no
re-run of a workflow, no dispatched bot sweep. The pipelines are fired only by the human
owner's dispatch or the remaining cron (`refresh-bot`). When an agent is asked to
implement, review, sweep or gather, it performs the same work on the host: its own
worktree cut from the fetched base (rule 6n), the bot targets the pipelines would have
run (`make implement-issue`, `make review-issue`, the four `search-*` legs,
`make pr-health`, the §6s fixes), a feature branch and a reviewed PR.

#### Scenario: the rulebook states both halves of the clause

- **Given** `AGENTS.md` rule 6t
- **When** the suite reads the rulebook
- **Then** it carries "no `gh workflow run` from a session", names the host path
  ("runs ON THE HOST", "the agent IS the bot, locally") with the bot targets it
  replaces, and states that only the human dispatch or the remaining cron fires the
  pipelines
- **Test:** tests/test_workflows.py::test_agents_md_forbids_an_agent_dispatching_a_pipeline

#### Scenario: a dropped or weakened clause turns CI red

- **Given** a change that removes the dispatch ban or the host-run sentence from 6t(e)
- **When** `make test` runs `test_agents_md_forbids_an_agent_dispatching_a_pipeline`
- **Then** the suite fails naming the missing clause, and the PR cannot auto-merge
- **Test:** tests/test_workflows.py::test_agents_md_forbids_an_agent_dispatching_a_pipeline
