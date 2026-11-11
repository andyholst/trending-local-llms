# openspec-task-gate

## ADDED Requirements

### Requirement: A task blocked on a human is a third state, accepted and reported

`openspec-tasks-check` MUST accept `- [~] <text> — blocked: <who/why>` in an active change's
`tasks.md`, MUST report it as a review-required change with the blocked line numbers, and MUST NOT
fail because of it. It MUST NOT report such a change as "all tasks checked".

#### Scenario: a blocked task passes the gate but is named as review-required

- **Given** an active change whose `tasks.md` is `- [x] 1. done` plus `- [~] 2. AGENTS.md row — blocked: owner approval (rule 3c)`
- **When** `check_all()` runs over that change tree
- **Then** it exits 0, prints `REVIEW-REQUIRED` naming the change, and prints the blocked line
- **Test:** tests/test_check_openspec_tasks.py::test_a_blocked_task_is_review_required_not_a_failure

### Requirement: A blocked task is neither done nor silently skipped

The gate MUST count a blocked box as unfinished: the change is never reported as fully checked, and
the root index MUST render its progress with the blocked count beside it (`done/total · N blocked`),
while a checklist with no blocked box renders exactly as before.

#### Scenario: the index shows the blocked task instead of a completed change

- **Given** a change whose `tasks.md` holds one `- [x]` and one `- [~] … — blocked: …` box
- **When** `scripts/openspec_index.py` renders the index
- **Then** its row shows `1/2 · 1 blocked`, and the gate never prints "all tasks checked" for it
- **Test:** tests/test_openspec_index.py::test_a_blocked_task_is_counted_as_blocked_not_done

### Requirement: A blocked task with no reason is a failure

A `- [~]` box MUST carry a `blocked:` annotation naming who or why. A bare `- [~]` MUST fail the
gate and be named by line, because an unannotated blocked box is an unchecked task wearing a third
state and would become the silent skip this gate exists to prevent.

#### Scenario: an unannotated blocked box fails loudly

- **Given** an active change with `- [~] 2. something, no reason given`
- **When** the task gate runs
- **Then** it exits 1 and names the change and the line of the unannotated box
- **Test:** tests/test_check_openspec_tasks.py::test_a_blocked_task_without_a_reason_fails

### Requirement: `make openspec-check` reports the blocked change instead of failing or lying

`make openspec-check` MUST stay green when the only unfinished work is blocked on a human, and its
closing line MUST NOT claim that every task is ticked — it MUST name the review-required report the
task gate printed.

#### Scenario: the CI gate's own words match what it found

- **Given** the `openspec-check` recipe in the `Makefile`
- **When** its echo line is read
- **Then** it names review-required blocked tasks rather than claiming every task is ticked
- **Test:** tests/test_check_openspec_tasks.py::test_wired_into_make_test
