# bot-agent-run-safety

## ADDED Requirements

### Requirement: A public target that runs the agent redacts its own stream

The redaction MUST live in the PUBLIC `make` target that runs the agent, not in each caller: a
workflow step, `scripts/fix_loop.sh` and a human all reach the agent through `make <target>`, so a
caller that has to remember is exactly how the fix loop was missed. The target MUST capture the
command's stream, print only the redactor's bounded tail, and exit with the command's own status.

WHEN a public target runs the agent,
THEN its recipe captures the stream, redacts it, prints at most the configured tail, and preserves the exit status.

#### Scenario: a target that lost the redaction is refused

- **Given** a `search-nvidia` recipe that calls the container directly
- **When** the secret-output guard runs over the tree
- **Then** it reports `agent-target-does-not-scrub`, naming the target

- **Test:** `tests/test_secret_output.py::test_a_public_agent_target_without_the_seam_is_a_violation`

#### Scenario: the shipped targets scrub

- **Given** the repository's `Makefile`
- **Then** every target in `AGENT_TARGETS_TO_SCRUB` redacts its own stream through the one seam

- **Test:** `tests/test_secret_output.py::test_the_shipped_agent_targets_scrub_their_own_stream`

#### Scenario: the seam itself must redact

- **Given** a `scrubbed_run` whose body no longer calls `scripts/scrub_log.py`
- **Then** the guard reports `scrub-seam-does-not-redact`, because every target trusting the seam would print raw
- **Test:** `tests/test_secret_output.py::test_a_public_agent_target_without_the_seam_is_a_violation`

#### Scenario: the seam prints the mask and keeps the status, driven for real

- **Given** the REAL `scrubbed_run` seam extracted from the Makefile and driven through `make` with a leaking command and a value in the environment
- **Then** the value never reaches make's console, the redacted tail does, the redacted copy is written, and a failing command still exits non-zero
- **Test:** `tests/test_scrub_log.py::test_the_seam_prints_only_the_redacted_tail_and_keeps_the_status`

### Requirement: A dynamic agent invocation is covered exactly when every leg self-scrubs

A workflow step calling the matrix form (`make search-${{ matrix.backend }}`, `make search-$…`) MUST
be recognised by the guard: it is safe exactly when every leg it can select redacts its own stream,
and it is a finding again the moment one leg loses the seam.

WHEN a step calls the agent through a substitution,
THEN the guard resolves it against the legs' own recipes.

#### Scenario: the matrix step is covered when every leg scrubs

- **Given** a `run: make search-${{ matrix.backend }}` and four legs that all call the seam
- **Then** the guard reports nothing
- **Test:** `tests/test_secret_output.py::test_the_matrix_search_step_is_covered_when_every_leg_scrubs`

#### Scenario: one un-scrubbed leg re-opens it

- **Given** the same step with one leg that no longer redacts
- **Then** the guard reports a finding
- **Test:** `tests/test_secret_output.py::test_the_matrix_search_step_is_covered_when_every_leg_scrubs`
