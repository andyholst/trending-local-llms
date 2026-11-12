# bot-agent-run-safety

## ADDED Requirements

### Requirement: The agent steps stream their agent to the job console live, masked

The shipped steps that run the agent (`issue-bot.yml`'s `Implement the issue`, `issue-review-bot.yml`'s
`Refine the issue` and `Review as a reply`) MUST run their public target UNCAPTURED — no step-level
redirect into a capture file, no after-the-fact `make scrub-log` — because the target itself pipes
the whole agent stream through `scripts/scrub_log.py --stream` before the console. A line the agent
writes MUST be readable on the job log (masked) BEFORE the agent process exits; the step's rc
contract (`rc=$?`, `exit $rc`, the rc=3 detach `::error::`) MUST survive the pipe unchanged.

#### Scenario: the first agent line arrives while the agent still runs

- **Given** the shipped `Implement the issue` step text (read from the workflow file) and the shipped seam shape
- **When** the agent writes its first line and stays running
- **Then** that line is on the step's console before the agent process exits, and the later lines arrive too
- **Test:** tests/test_implement_stream.py::test_a_line_reaches_the_console_while_the_agent_is_still_running

#### Scenario: the shipped steps run the targets uncaptured and keep the rc contract

- **Given** `issue-bot.yml` and `issue-review-bot.yml`
- **When** their three agent steps' `run:` text is read
- **Then** each runs `make implement-issue` / `make review-issue` / `make review-issue-window` with no capture redirect and no `make scrub-log`, and each captures `rc=$?` (the reviewer steps still `exit $rc`, rc=3 names the detach)
- **Test:** tests/test_implement_stream.py::test_the_shipped_steps_stream_their_targets_uncaptured

#### Scenario: the reviewer detach contract survives the refactor

- **Given** the shipped `Refine the issue` step with an agent that exits 3 (Hermes detaching for input, #549)
- **When** the step runs
- **Then** the step exits 3 and prints the named `::error::` line
- **Test:** tests/test_implement_stream.py::test_the_reviewer_steps_keep_the_detach_contract

### Requirement: The live stream carries no secret value in any spelling, and both captures stay honest

While the agent streams, no spelling of a credential (raw, URL-encoded, base64, a credential shape)
MAY reach the job console; the masked line stays readable (`***`), and the seam's own artifacts stay
honest: the gitignored RAW capture keeps the value (the log stays whole for the repo's own readers),
the redacted copy (the uploaded artifact) does not carry it.

#### Scenario: every spelling stays masked while streaming

- **Given** the shipped implement step and seam shape with a planted value and a planted token shape
- **When** the stream runs
- **Then** none of the raw, URL-encoded or base64 spellings appears on the console, the masked line does, the raw capture keeps the value and the scrubbed artifact does not
- **Test:** tests/test_implement_stream.py::test_the_live_console_carries_no_value_in_any_spelling

#### Scenario: the shipped implement step prints no value end to end

- **Given** the shipped Makefile recipe for `implement-issue` executed against a stub `docker` streaming planted values through the real redactor
- **When** the recipe runs
- **Then** the console shows the agent's safe lines masked and never the value in any spelling
- **Test:** tests/test_scrub_log.py::test_the_shipped_implement_step_prints_no_value_in_any_spelling

### Requirement: Every agent-running public target is on the guard's scrub list

The public targets that run the agent — the search legs, `fix`, `implement-issue`, `review-issue`,
`review-issue-window` — are ONE list in `scripts/check_secret_output.py` (`AGENT_TARGETS_TO_SCRUB`),
and `agent-target-does-not-scrub` MUST refuse any of them whose recipe no longer pipes its stream
through the seam; a step that runs an agent target with nothing redacting it stays refused. Tests
MUST seed the guard's own list, never a copy of it.

#### Scenario: the three bot-leg targets' recipes carry the seam

- **Given** the repository Makefile
- **When** `make check-secret-output` reads `implement-issue`, `review-issue` and `review-issue-window`
- **Then** each recipe passes its `$(DOCKER_RUN)` through `$(call scrubbed_run, …)`, and removing the seam turns the check red
- **Test:** tests/test_implement_stream.py::test_the_shipped_targets_own_the_live_seam

#### Scenario: a matrix step is covered exactly when every leg on the list scrubs

- **Given** a planted fixture whose Makefile defines every target on the guard's OWN list, each scrubbing
- **When** `make search-${{ matrix.backend }}` runs in a step
- **Then** the check is clean; breaking one leg's recipe makes it report that leg
- **Test:** tests/test_secret_output.py::test_the_matrix_search_step_is_covered_when_every_leg_scrubs
