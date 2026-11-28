## ADDED Requirements

### Requirement: The weekly auto-bump cadence lives in the Renovate App config

The repository SHALL carry one root `renovate.json5` whose app-side `schedule` is weekly and whose `timezone` is explicit. It SHALL enable the `github-actions` and `dockerfile` managers so pinned Action SHAs and Dockerfile base-image versions are bumped, and SHALL keep bumps small with `separateMultipleMajor` and a dependency dashboard. A missing, empty or cadence-less config SHALL be refused by the guard.

#### Scenario: The app config is present with a weekly cadence

- **Given** the fetched base tree with the change applied
- **When** the guard reads `renovate.json5`
- **Then** the file exists, is non-empty, declares a weekly `schedule` and a `timezone`, and enables both bump managers
- **Test:** tests/test_workflows.py::test_renovate_app_config_carries_the_weekly_cadence_without_a_workflow_cron

#### Scenario: The config is missing or empty

- **Given** a tree with no `renovate.json5`, or an empty one
- **When** the guard runs
- **Then** it fails loudly instead of silently allowing an unconfigured robot
- **Test:** tests/test_workflows.py::test_renovate_app_config_carries_the_weekly_cadence_without_a_workflow_cron

### Requirement: No repository workflow owns the Renovate cadence

No workflow SHALL carry a Renovate `on.schedule`. Rule 6t / #1029 leaves `refresh-bot.yml` as the only pipeline with a cron; a Renovate workflow that gains one SHALL be refused by the guard, because the cadence belongs to the App config.

#### Scenario: A Renovate workflow gains a weekly cron

- **Given** a `.github/workflows/renovate.yml` with an `on.schedule` block
- **When** the guard scans every workflow
- **Then** it fails, naming that workflow, while refresh-bot's two legitimate slots stay acceptable
- **Test:** tests/test_workflows.py::test_renovate_app_config_carries_the_weekly_cadence_without_a_workflow_cron
