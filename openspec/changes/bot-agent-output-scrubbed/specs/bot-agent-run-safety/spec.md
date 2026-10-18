# bot-agent-run-safety

## ADDED Requirements

### Requirement: Every headless agent call passes the whole non-interactive flag set

A `hermes -z` recipe MUST pass the non-interactive flag set from ONE Makefile variable
(`HERMES_NONINTERACTIVE`), because `--yolo` alone does not cover every approval channel:
`--accept-hooks` is a separate flag, and a request for input in a `-z` run makes the agent
**detach** instead of proceeding or failing (`Input required; detached without cancelling`).
A recipe that passes only part of the set is a defect, whoever writes it.

WHEN a `hermes -z` recipe is added or edited,
THEN its continuation line carries `$(HERMES_NONINTERACTIVE)` and that variable names both `--yolo` and `--accept-hooks`.

#### Scenario: a recipe carrying only `--yolo` is refused

- **Given** a Makefile recipe whose `hermes -z` continuation line ends `--reasoning low --yolo`
- **When** the prompt-shape guard runs
- **Then** it fails, naming the recipe and the missing flag set

- **Test:** `tests/test_hermes_prompts.py::test_every_headless_agent_call_passes_the_noninteractive_flag_set`

#### Scenario: the shipped Makefile passes the whole set

- **Given** the repository's `Makefile`
- **Then** `HERMES_NONINTERACTIVE` contains `--yolo` and `--accept-hooks`, and every `hermes -z` continuation line uses the variable

- **Test:** `tests/test_hermes_prompts.py::test_the_shipped_recipes_use_the_noninteractive_variable`

### Requirement: An agent's console output carries no secret value

A bot job MUST NOT print an agent's raw stream. Before any of it reaches the log the
stream MUST be redacted against the secret VALUES present in the environment (read by
name, never echoed) and against token shapes, and the printed part MUST be bounded to a
tail. Redaction is not optional: GitHub masks only the values it registers, so a
transformed value (URL-encoded, base64, a slice) would otherwise pass through.

WHEN a bot job runs an agent and wants its output visible,
THEN it captures the stream to a file, redacts it, prints at most a bounded tail, and uploads the redacted file — never the raw one.

#### Scenario: a value in the log is replaced, however it is spelled

- **Given** a log containing a secret value raw, URL-encoded and base64-encoded, and a token-shaped literal
- **When** the redactor runs with that value in the environment
- **Then** none of those spellings appears in the output, and no environment value is printed

- **Test:** `tests/test_scrub_log.py::test_every_spelling_of_the_value_is_replaced`

#### Scenario: the printed output is bounded

- **Given** a log longer than the tail the caller asked for
- **Then** the printed lines are at most that many, and the redacted file holds the whole log

- **Test:** `tests/test_scrub_log.py::test_the_printed_output_is_bounded_to_the_tail`

#### Scenario: the shipped implement step leaks nothing, driven end to end

- **Given** the workflow's OWN implement step text, run against a stub `make` whose agent stream carries the value raw, in a Bearer header and as a token shape
- **Then** none of those spellings reaches the step's console output, the redacted artifact is written, and a failing `rc` still reports `implemented=false`
- **Test:** `tests/test_scrub_log.py::test_the_shipped_implement_step_prints_no_value_in_any_spelling`

#### Scenario: a missing or unreadable log is loud

- **Given** a path that does not exist
- **Then** the redactor exits non-zero naming the path, instead of printing nothing and passing

- **Test:** `tests/test_scrub_log.py::test_a_missing_log_is_loud`

### Requirement: A captured stream is never printed raw

A workflow `run:` block that redirects a command's stream into a log file MUST also run
the redactor in the same block, and MUST NOT print that file (`cat`, `head`, `tail`,
`less`) itself. Capturing to a file is only safe together with the redaction step; on its
own it is a raw stream one edit away from the console.

WHEN a step captures a stream to a log file,
THEN the same step calls the redactor through `make`, and no step prints the raw file.

#### Scenario: a capture without redaction is refused

- **Given** a step whose `run:` is `make implement-issue > implement.log 2>&1` with no redactor call
- **Then** the secret-output guard reports the missing redaction, naming the file and line

- **Test:** `tests/test_secret_output.py::test_a_captured_stream_without_redaction_is_a_violation`

#### Scenario: printing the captured file is refused

- **Given** a step containing `cat implement.log`
- **Then** the guard reports the raw print, naming the file and line

- **Test:** `tests/test_secret_output.py::test_printing_the_captured_log_is_a_violation`

### Requirement: A step never runs the agent with its stream going to the console

A workflow `run:` block that executes an AGENT target (`make implement-issue`,
`make review-issue`, `make review-issue-window`, `make search-<backend>`) MUST capture
the stream and print only the redactor's bounded output. Naming a target in a message is
not running it, so a diagnostic that merely mentions one is not a finding.

WHEN a step runs an agent target,
THEN the block captures that call's stream and calls the redactor, and no raw agent line reaches the step's console output.

#### Scenario: an inline agent run is refused

- **Given** a step whose `run:` is `make review-issue` (the reviewer's body path before this change)
- **When** the secret-output guard runs over the tree
- **Then** it reports `agent-stream-printed-raw`, naming the file and line

- **Test:** `tests/test_secret_output.py::test_an_agent_stream_printed_raw_is_a_violation`

#### Scenario: the captured shape is clean

- **Given** a step that runs the agent into a log file and then `make scrub-log FILE=…`
- **Then** the guard reports nothing
- **Test:** `tests/test_secret_output.py::test_a_captured_agent_run_is_clean`

#### Scenario: naming the target in a message is not running it

- **Given** `echo "::error::… (make implement-issue rc=2)."`
- **Then** the guard reports nothing
- **Test:** `tests/test_secret_output.py::test_a_mention_of_an_agent_target_in_a_message_is_not_a_violation`

### Requirement: The leak scan covers the run logs, and a value found in one is rotated

The scan over the tree is not enough: a credential that reaches a *log* never touches the tree,
and GitHub masks only the values it registers. An agent that changes any way output reaches a log
MUST audit the real pipeline — the affected runs' logs and artifacts — for every secret name's
value in every spelling plus the credential shapes, and a value found in a log or an artifact MUST
be rotated in the provider and in the repo secret. AGENTS.md MUST carry this rule, because the
guard over the tree cannot see a run-time value.

WHEN an agent changes what a bot prints,
THEN it audits the affected runs' logs and artifacts, and AGENTS.md states the rule and the rotation consequence.

#### Scenario: the rule is in AGENTS.md and a test keeps it there

- **Given** `AGENTS.md` §3d, the secret rules
- **Then** it names the run logs as in scope, the `gh run view <id> --log` audit, the rotation, and that a GitHub mask is not a pass — and a test fails if any of those leaves the file
- **Test:** `tests/test_secret_output.py::test_agents_md_requires_the_run_log_audit_and_rotation`

### Requirement: The shipped implement step prints only the redacted tail

The implementer's implement step MUST capture the agent's stream to a gitignored file,
print only the redactor's bounded output, and upload the REDACTED log as the run artifact.
The step's refusal contract is unchanged: a non-zero `rc` from `make implement-issue` MUST
still fail the run.

WHEN the implement step runs,
THEN the step's console output holds no unredacted line of the agent stream, the uploaded artifact is the redacted log, and a non-zero `rc` still fails the run.

#### Scenario: the shipped step is the captured-and-redacted shape

- **Given** `.github/workflows/issue-bot.yml`
- **Then** the implement step's `run:` text captures to a log file, calls `make scrub-log`, prints no raw file, and uploads the redacted log

- **Test:** `tests/test_workflows.py::test_issue_bot_scrubs_the_agent_stream_before_it_reaches_the_log`

#### Scenario: a failed implementation is still red

- **Given** a `make implement-issue` that exits non-zero
- **Then** the run's loud-failure step still fails, so a run that implemented nothing can never look green

- **Test:** `tests/test_workflows.py::test_issue_bot_scrubs_the_agent_stream_before_it_reaches_the_log`
