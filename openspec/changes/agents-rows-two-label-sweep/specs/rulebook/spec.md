# rulebook

## ADDED Requirements

### Requirement: §6j states that the sweep reads every actionable label as one queue

`AGENTS.md` §6j MUST say that the implementer's sweep reads BOTH actionable labels
(`data-gap-analysis` and `tech-debt`) as ONE oldest-first queue, one issue per run, so the two
compete on AGE rather than on which list was read first — and that the reviewer keeps its own
`data-gap-analysis` default, so a `tech-debt` body is never silently refined.

#### Scenario: the two-label queue is described, and what it fixes

- **Given** `AGENTS.md` §6j as rule 6d/6j define the queue
- **When** a reader looks for the implementer's label set
- **Then** it names `data-gap-analysis` **and** `tech-debt`, says ONE queue oldest-first, one
  issue per run, and names the measured consequence (the `tech-debt` findings that had no
  reader)
- **Test:** `tests/test_agents_rows.py::test_the_rows_for_the_two_label_queue_and_the_sweep_alarm_are_written`

#### Scenario: the reviewer's narrower default is not lost

- **Given** §6j as rewritten
- **When** it describes the reviewer
- **Then** it says the reviewer keeps its own `data-gap-analysis` default, so a `tech-debt` body
  is not silently refined
- **Test:** `tests/test_agents_rows.py::test_the_rows_for_the_two_label_queue_and_the_sweep_alarm_are_written`

### Requirement: §6e states the triage verdict and the tree-evidence gate

`AGENTS.md` §6e MUST describe the implementer's `triage.md` verdict (`implement` / `refine` /
`close`) taken against the base it fetched, the `make issue-verdict` application of it, and the
REFUSAL of a `close` or `refine` whose `EVIDENCE:` names no `path:line`, checkable path or
`make`/`python3`/`gh` command.

#### Scenario: the verdict, its three values and its refusal are described

- **Given** `AGENTS.md` §6e
- **When** a reader looks for how an implementation run decides an issue is stale
- **Then** it names `triage.md`, the three verdicts, `make issue-verdict`, and that an
  `EVIDENCE:` block pointing at nothing is REFUSED — a stale issue closed on proof, never prose
- **Test:** `tests/test_agents_rows.py::test_the_rows_for_the_two_label_queue_and_the_sweep_alarm_are_written`

#### Scenario: the gate the code enforces really exists

- **Given** `scripts/issue_verdict.py`, the one implementation
- **When** the pin reads it
- **Then** it carries an `EVIDENCE:` shape check that refuses prose-only evidence
- **Test:** `tests/test_agents_rows.py::test_the_rows_name_modules_that_exist`

### Requirement: §6b states the implementer's second schedule slot

`AGENTS.md` §6b's `issue-bot.yml` bullet MUST name the second cron slot (`49 * * * *` beside
`19 * * * *`), why it exists (GitHub delays or drops crons — the `refresh-bot` lesson that the
delivery alarm #497 exists for), that `concurrency: issue-bot-<n>` serialises the slots, and
that an idle sweep is a green no-op.

#### Scenario: both slots and their reason are named

- **Given** `AGENTS.md` §6b's implementer bullet
- **When** a reader checks the trigger surface
- **Then** it names both cron slots and the dropped-cron reason, and the pipeline really carries
  both
- **Test:** `tests/test_agents_rows.py::test_the_rows_for_the_two_label_queue_and_the_sweep_alarm_are_written`

### Requirement: §8 carries the rows the two changes owed

`AGENTS.md` §8 MUST carry a row for each guard the owed rows name — the two #494 tests and
`tests/test_sweep_alarm.py` / `make sweep-alarm` (#497) — each naming the module it lives in and
the failure it catches.

#### Scenario: the three rows are present and describe their guards

- **Given** `AGENTS.md` §8
- **When** the pin searches for the guards
- **Then** `test_three_mock_issues_decide_implement_refine_or_close_against_the_tree`,
  `test_the_queue_reads_both_labels_as_one_oldest_first_list` and `tests/test_sweep_alarm.py` are
  each inside a row that names its measured failure
- **Test:** `tests/test_agents_rows.py::test_the_rows_for_the_two_label_queue_and_the_sweep_alarm_are_written`

#### Scenario: the §8 table still parses

- **Given** §8 after the rows are appended
- **When** it is parsed as a markdown table
- **Then** it still has its header and every row carries a guard and a description
- **Test:** `tests/test_agents_rows.py::test_the_section_still_parses_as_a_table`
