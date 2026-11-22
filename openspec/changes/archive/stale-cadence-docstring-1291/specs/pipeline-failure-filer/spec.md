## ADDED Requirements

### Requirement: The filer's module docstring names its dispatch-only entry point

`scripts/pipeline_failure_issue.py`'s module docstring SHALL name `queued-alarm.yml` as the
filer's entry point and SHALL state that it is dispatch-only (no `on.schedule`). It SHALL NOT
claim a weekly or Wednesday cadence.

#### Scenario: The docstring carries no weekly or Wednesday cadence claim

- **Given** the module docstring of `scripts/pipeline_failure_issue.py` at the changed head
- **When** the docstring is read
- **Then** it names `queued-alarm.yml`, states the entry point is dispatch-only, and contains
  neither a weekly nor a Wednesday cadence claim
- **Test:** tests/test_pipeline_failure_issue.py::test_the_module_docstring_names_the_dispatch_only_entry_point

#### Scenario: The docstring agrees with the workflow's own triggers

- **Given** `.github/workflows/queued-alarm.yml` at the changed head
- **When** its `on:` block is read
- **Then** it declares no `schedule` trigger, matching the docstring's dispatch-only claim
- **Test:** tests/test_pipeline_failure_issue.py::test_the_module_docstring_names_the_dispatch_only_entry_point
