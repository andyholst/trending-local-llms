## ADDED Requirements

### Requirement: The Renovate guard parses the real app config as JSON5

The workflow-wiring guard SHALL read `renovate.json5` from disk and PARSE it, never decide from substrings: a small tested helper SHALL strip `//` and `/* */` comments and trailing commas outside string literals (honouring escaped quotes), and the guard SHALL call `json.loads` on the result. A syntactically broken config — trailing commas or a dropped closing brace — SHALL be refused even when every expected token still appears in its text. The shipped config, which legitimately carries `//` comments, SHALL parse and pass.

#### Scenario: The shipped config parses and carries its values

- **Given** the real `renovate.json5` at the repository root, with its rule-6t `//` comments
- **When** the guard strips comments/trailing commas and parses the object
- **Then** it reports a parse pass, a weekly `schedule`, an explicit `timezone`, `github-actions` and `dockerfile` in `enabledManagers`, and both `separateMultipleMajor` and `dependencyDashboard` as `True`
- **Test:** tests/test_workflows.py::test_renovate_app_config_carries_the_weekly_cadence_without_a_workflow_cron

#### Scenario: A syntactically broken config is RED

- **Given** a real on-disk config with trailing commas and a missing closing brace but all expected substrings
- **When** the guard runs against that file
- **Then** the parse check and the parsed-value checks fail, naming the JSON error, while the workflow-cron checks still pass
- **Test:** tests/test_workflows.py::test_renovate_app_config_carries_the_weekly_cadence_without_a_workflow_cron

### Requirement: The comment/trailing-comma stripper respects strings

The stripper used by the guard SHALL remove both comment forms and trailing commas only outside string literals. A `//` inside a URL, a `/*` inside a value, a comma or brace inside a quoted string, and an escaped quote SHALL survive unchanged, and the stripped text SHALL be strict JSON.

#### Scenario: Comment markers and commas inside strings survive

- **Given** a JSON5 text containing a URL with `//`, a value with `/*`, a quoted string with `,} //`, an escaped quote, and trailing commas in an array and object
- **When** `json5_to_json` reduces it
- **Then** comments and trailing commas outside strings are gone, every in-string marker is intact, and `json.loads` returns the original values
- **Test:** tests/test_workflows.py::test_renovate_json5_helper_strips_comments_and_trailing_commas_without_touching_strings

### Requirement: No repository workflow owns the Renovate cadence

No workflow SHALL carry a Renovate `on.schedule`; rule 6t / #1029 leaves `refresh-bot.yml` as the only pipeline with a cron. The existing per-workflow scan SHALL remain in force unchanged.

#### Scenario: A Renovate workflow gains a weekly cron

- **Given** a `.github/workflows/renovate.yml` with an `on.schedule` block
- **When** the guard scans every workflow
- **Then** it fails naming that workflow, while the legitimate refresh-bot slots stay acceptable
- **Test:** tests/test_workflows.py::test_renovate_app_config_carries_the_weekly_cadence_without_a_workflow_cron
