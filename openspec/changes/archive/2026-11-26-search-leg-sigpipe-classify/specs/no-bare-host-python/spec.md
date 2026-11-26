# no-bare-host-python

## ADDED Requirements

### Requirement: A silent agent SIGPIPE is classified, not hidden

The shared `scrubbed_run` redaction seam SHALL inspect the producer's pipeline status and, when it is 141 (SIGPIPE), SHALL print a classified `quiet/agent-failed` failure naming issue #1747 before returning the producer's original status. The redacted capture, the `$(PYTHON_RUN)` seam and the command's own exit status SHALL be unchanged.

#### Scenario: a search leg closes its stream with no lines

- **Given** the Makefile macro that pipes an agent leg into `scrub_log.py --stream`
- **When** the producer exits 141 after the redactor has captured zero lines
- **Then** the job log contains the classified `quiet/agent-failed` SIGPIPE failure, the macro still exits 141, and the guard fails on the previous unclassified seam
- **Test:** tests/test_os_agnostic_make.py::test_the_redaction_seam_classifies_a_silent_agent_sigpipe
