## ADDED Requirements

### Requirement: A superseded cancelled push-to-master run files nothing

A `push`-to-`master` run whose conclusion is `cancelled` and whose jobs yielded no failing step,
no `make` target and no readable error block SHALL NOT become a tracked failure, an issue or a
ledger row. GitHub cancels the older validation when a newer push lands, so such a run never
concluded a delivery and carries no failure text to file (rule 6r). The skip SHALL be announced by
the sweep, in `--dry` as well as live, naming how many superseded runs were dropped.

#### Scenario: Nine cancelled push-to-master runs with unreadable logs

- **Given** nine in-window `event=push`/`headBranch=master`/`conclusion=cancelled` runs whose job
  logs cannot be read (`gh: HTTP 404`)
- **When** the master/schedule half of the filer sweeps its window
- **Then** no issue is filed for them and no ledger row names any of their run ids
- **Test:** tests/test_pipeline_failure_issue.py::test_a_cancelled_push_run_is_not_filed

#### Scenario: The skip is previewed and counted

- **Given** the same nine superseded runs and a `--dry` sweep
- **When** the sweep previews its work
- **Then** it prints one announcement naming the number of superseded runs dropped and writes
  neither an issue nor a ledger
- **Test:** tests/test_pipeline_failure_issue.py::test_the_superseded_skip_is_announced_in_dry_output

### Requirement: The skip never swallows a real diagnosis

A cancelled run whose log DID yield a failing step, `make` target or error block SHALL still file
exactly as before (issue #1615), and a `cancelled` `schedule` run — a dropped delivery, which
`BAD_CONCLUSIONS` deliberately keeps — SHALL still be tracked even when its log is unreadable
(filed `UNDIAGNOSED`, loudly).

#### Scenario: A cancelled push run with a readable error block

- **Given** one `event=push`/`headBranch=master`/`conclusion=cancelled` run whose cancelled job's
  log carries a real error block
- **When** the sweep collects it
- **Then** exactly one issue is filed and its ledger row carries the diagnosis
- **Test:** tests/test_pipeline_failure_issue.py::test_a_cancelled_push_run_with_a_readable_diagnosis_still_files

#### Scenario: A cancelled schedule run with an unreadable log

- **Given** one `event=schedule`/`conclusion=cancelled` run whose log cannot be read
- **When** the sweep collects it beside the nine superseded push runs
- **Then** the schedule run is filed `UNDIAGNOSED` while the nine push runs file nothing
- **Test:** tests/test_pipeline_failure_issue.py::test_a_cancelled_push_run_is_not_filed
