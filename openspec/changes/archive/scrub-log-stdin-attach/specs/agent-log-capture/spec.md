## ADDED Requirements

### Requirement: The live redactor owns an attached stdin

The streamed capture SHALL reach `scripts/scrub_log.py --stream` through a container harness
whose stdin is the producer pipe. The harness SHALL be scoped to the redactor end: the shared
`PYTHON_RUN` SHALL keep its detached stdin, and both harnesses SHALL be built from the same
flags plus `-i` only on the scoped sibling. `bash -o pipefail`, `PIPESTATUS[0]`, the
`--stream --append --raw --out` contract, the producer's exit status and the #1747 SIGPIPE
classification line SHALL remain unchanged. No retry, SKIP or classifier branch SHALL be added.

#### Scenario: A delayed talking agent is captured and redacted live

- **Given** the shipped `scrubbed_run` seam and an agent that emits four lines with a credential SHAPE after a short delay
- **When** the stream is run through the scoped stdin-attached harness
- **Then** all four lines are printed and written masked, the summary reports 4 lines and 1 redaction, the mask is in the REDACTED artifact, the token is only in the RAW artifact and never on the console, and the producer exits 0
- **Test:** tests/test_scrub_log_stdin.py::test_the_shipped_seam_captures_and_redacts_a_delayed_agent

#### Scenario: The pre-change detached harness loses the whole stream

- **Given** the pre-#1810 redactor end, whose `docker run` has no `-i`
- **When** the same delayed talking producer runs through it
- **Then** the summary reports 0 lines and 0 redactions, no `[agent]` line is captured, the #1747 SIGPIPE classification is printed and make reports Error 141
- **Test:** tests/test_scrub_log_stdin.py::test_the_pre_change_harness_loses_every_line

#### Scenario: A silent agent and an outage keep their verdicts

- **Given** a planted agent that emits nothing and the real `zero_hit_verdict` classifier
- **When** the attached seam streams it, then quiet and all-outage stats are classified
- **Then** the seam adds no retry or SKIP, stays green with 0 lines, and the unchanged classifier returns quiet/1 for a reachable mirror and outage/0 for a total outage
- **Test:** tests/test_scrub_log_stdin.py::test_a_silent_agent_is_not_retried_and_the_verdict_stays_put

#### Scenario: The producer's own failure status survives the pipe

- **Given** an agent that sleeps and exits 7 through the attached seam
- **When** the pipeline finishes
- **Then** pipefail reports the producer's status, not the redactor's, and make names Error 7
- **Test:** tests/test_scrub_log_stdin.py::test_a_red_producer_keeps_its_own_status_through_the_attached_pipe

#### Scenario: The shared harness stays literal and the two flag sets cannot drift

- **Given** the shipped Makefile and the pre-#1810 `PYTHON_RUN` definition
- **When** the two harness definitions are compared
- **Then** `PYTHON_RUN` keeps its literal #1496 flags and the scoped definition is identical except for its single `-i`
- **Test:** tests/test_scrub_log_stdin.py::test_the_two_harnesses_carry_the_same_flags

#### Scenario: The guard suite recognises the scoped seam only

- **Given** the real Makefile, `check_no_bare_host_python` and `check_secret_output`
- **When** the guards inspect the shipped seam
- **Then** `-i` appears on the scoped redactor harness and not on the shared one, the no-bare-host guard reports no violation, and the secret-output guard still sees the live `--stream` redactor with no bare host replacement
- **Test:** tests/test_scrub_log_stdin.py::test_the_guard_detectors_accept_the_scoped_redactor_only
