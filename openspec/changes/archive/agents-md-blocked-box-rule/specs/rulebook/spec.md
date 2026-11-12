# rulebook

## ADDED Requirements

### Requirement: The rulebook states the blocked-box state of the task gate

`AGENTS.md` §6f MUST name the blocked state in the same sentence as "no
unticked box": a `- [~] … — blocked: <who/why>` box is a review-required
change, is reported, and is never counted as done.

#### Scenario: a reader reads the gate sentence

- **Given** `AGENTS.md` §6f's `make openspec-check` sentence
- **When** the reader asks whether a blocked step may sit unticked
- **Then** the sentence names the blocked box shape and says it is reported
  and never counted as done, beside "no unticked box"
- **Test:** tests/test_check_openspec_tasks.py::main

### Requirement: The §8 row names the blocked-box annotation rule

`AGENTS.md` §8's `tests/test_check_openspec_tasks.py` row MUST name both
blocked checks: a `- [~]` box blocked WITH a reason passes and is reported as
review-required; a `- [~]` box blocked WITHOUT a reason fails the gate.

#### Scenario: a reader asks what the task gate refuses

- **Given** `AGENTS.md` §8's row for `tests/test_check_openspec_tasks.py`
- **When** the reader asks whether a blocked box may pass
- **Then** the row states both halves of the annotation rule (with-reason
  passes and is reported; without-reason fails)
- **Test:** tests/test_check_openspec_tasks.py::main
