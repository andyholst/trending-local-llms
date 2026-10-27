# bot-agent-run-safety

## ADDED Requirements

### Requirement: A round's progress reaches the job log while the round runs

The `scrubbed_run` seam MUST feed the command's stream through the redactor LIVE — each line masked
BEFORE it is printed and flushed at once — instead of capturing the whole stream and printing its
tail after the command has exited. Redaction MUST stay in the path (the masked line is what is
printed; the RAW capture is written to the gitignored file and never printed or uploaded), the
REDACTED copy MUST be written for the run artifact, and the recipe MUST return the COMMAND's exit
status rather than the redactor's.

WHEN a target that runs the agent through the seam executes,
THEN a line the command writes is visible on the console before the command exits, masked, and a
failing command still fails the recipe.

#### Scenario: a line is printed while the stream is still open

- **Given** the redactor in `--stream` mode with a `--raw` and an `--out` path
- **When** one line is written to its stdin and stdin stays open
- **Then** that line appears on stdout before the process exits, with the secret value masked and both files written
- **Test:** tests/test_scrub_log.py::test_stream_mode_prints_a_line_while_the_stream_is_still_open

#### Scenario: the seam shows a round while it runs and keeps the status

- **Given** the repository's own `scrubbed_run` recipe driving a command that prints, sleeps, then prints
- **Then** the first line is readable before the command finishes and a failing command still reports its own exit code
- **Test:** tests/test_scrub_log.py::test_the_seam_shows_a_round_while_it_runs

#### Scenario: a live stream with nowhere to write its artifact is refused

- **Given** `--stream` with no `--out`, `--stream` combined with `--in`, or neither mode at all
- **Then** each shape exits non-zero instead of losing the artifact or the source
- **Test:** tests/test_scrub_log.py::test_stream_mode_needs_an_artifact_and_refuses_a_mixed_mode

### Requirement: The container's stdio is unbuffered

The run wrapper MUST set `PYTHONUNBUFFERED=1` explicitly (`-e NAME=value`, never a forwarded host
value that may be unset), because `docker run` gives the container a pipe and a block-buffered child
writes nothing until it exits — which makes even a streaming host silent.

WHEN the container is started through the run wrapper,
THEN every Python child flushes each line into the stream the redactor reads.

#### Scenario: the shipped wrapper is unbuffered

- **Given** the repository's `Makefile`
- **Then** its `DOCKER_RUN` wrapper carries `-e PYTHONUNBUFFERED=1`
- **Test:** tests/test_scrub_log.py::test_the_container_stdio_is_unbuffered

### Requirement: A seam that prints only after the command ends is refused

`make check-secret-output` MUST refuse a `scrubbed_run` seam that captures the stream and prints a
tail after the command exits, naming the rule and the measured silence. An end-of-run redaction is a
post-mortem: it is safe and it hides every repair in flight.

WHEN the seam no longer feeds the stream through the redactor's live mode,
THEN the guard reports `scrub-seam-is-not-live` and the PR is red.

#### Scenario: the pre-change seam is a violation

- **Given** a `scrubbed_run` seam shaped `> log 2>&1` then `scrub-log --in log`, in a tree with it
- **Then** the guard reports `scrub-seam-is-not-live`
- **Test:** tests/test_secret_output.py::test_a_seam_that_prints_only_after_the_command_ends_is_a_violation

#### Scenario: the shipped seam is accepted

- **Given** the repository's own `Makefile`
- **Then** `seam_streams` accepts it, so the live shape is what the tree ships
- **Test:** tests/test_secret_output.py::test_a_seam_that_prints_only_after_the_command_ends_is_a_violation
