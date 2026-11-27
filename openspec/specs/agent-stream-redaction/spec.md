# agent-stream-redaction Specification

## Purpose
TBD - created by archiving change scrub-run-attach-stdin. Update Purpose after archive.

## Requirements

### Requirement: The redactor's Docker run attaches stdin so the live agent stream is captured

`PYTHON_RUN` SHALL include `-i` on its `docker run`, so the `scrubbed_run` pipe
(`cmd | $(PYTHON_RUN) python3 scripts/scrub_log.py --stream …`) forwards the
producer's live stream into the redactor. The redactor SHALL read the streamed
lines, print each masked `[agent]` line, and report a non-empty stream; the
producer SHALL keep its own success status. The `#1747` SIGPIPE classification and
the `pipefail` exit-status contract in `scrubbed_run` SHALL remain in place, so a
genuinely dead agent is still refused rather than skipped or retried.

#### Scenario: A delayed producer's lines reach the redactor

- **Given** the shipped `scrubbed_run` seam and shipped `PYTHON_RUN` definition in a fixture Makefile, a stand-in Docker CLI on `PATH` that emulates Docker's stdin rule (`-i` forwards, no `-i` closes it), and a producer that sleeps then prints two lines
- **When** `make stream` runs the producer through the seam
- **Then** both `[agent]` lines reach the console, the scrubber reports a non-empty stream, no SIGPIPE classification is printed, and the target exits 0
- **Test:** tests/test_scrubbed_run_seam.py::test_the_redactor_attaches_stdin_so_the_agent_stream_is_captured

#### Scenario: The unfixed seam reproduces the SIGPIPE 141

- **Given** the same fixture but with the pre-change `PYTHON_RUN` (no `-i`)
- **When** `make stream` runs the delayed producer through the seam
- **Then** the scrubber reports zero lines, the producer ends with SIGPIPE (exit 141) and the `#1747` classification is printed, proving the guard is RED on the old code
- **Test:** tests/test_scrubbed_run_seam.py::test_the_redactor_attaches_stdin_so_the_agent_stream_is_captured

#### Scenario: The anti-vacuous classification survives the fix

- **Given** the fixed seam and a producer that emits nothing
- **When** `make quiet` runs that producer through the seam
- **Then** no redacted `[agent]` line is fabricated, the `SIGPIPE (exit 141)` classification and the `exit "$$st"` status contract are still present in the shipped seam, so a genuinely dead agent remains refused
- **Test:** tests/test_scrubbed_run_seam.py::test_the_redactor_attaches_stdin_so_the_agent_stream_is_captured
