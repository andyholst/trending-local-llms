## ADDED Requirements

### Requirement: A repeat unregistered-engine WARN fails the engine check

`make engine-check` (`scripts/engine_registry.py --check-raw`) SHALL treat the
age of every unregistered engine spelling as part of its verdict. The first-seen
date of a spelling SHALL be the oldest dated raw capture (`<backend>-YYYYMMDD-HHMMSS.json`)
that names it; no separate state file SHALL be introduced. A WARN decision first
seen within `--refresh-window-days` (default 7) SHALL be reported as new and the
check SHALL exit 0. A WARN decision first seen OLDER than the window SHALL be
reported as a REPEAT naming its first-seen date and age, and the check SHALL
exit 1 naming the repeat engines and their resolutions (register the engine,
declare the spelling in `ENGINE_NAME_ALIASES`, or decline it in `NON_ENGINE_REPOS`
/ `NON_ENGINE_NAMES`). A decision already settled — the engine registered, or the
spelling declined by the `NON_ENGINE_*` lists — SHALL report OK and SHALL never
count as a repeat. A spelling named only in undated captures SHALL report
`first seen unknown` and SHALL never count as a repeat.

#### Scenario: A WARN older than the refresh window fails the check

- **Given** a raw capture dated 10 days before `--now` naming an unregistered
  engine spelling with no `engine_repo`
- **When** `engine_registry.py --check-raw <dir> --now <date>` runs
  (default 7-day window)
- **Then** the line names the engine with `first seen <date>` and
  `REPEAT past one refresh (7d)`, the summary names its resolutions, and the
  exit code is 1
- **Test:** tests/test_engine_registry.py::test_repeat_warn_fails_the_check

#### Scenario: A WARN first seen within the window stays report-only

- **Given** a raw capture dated 2 days before `--now` naming an unregistered
  engine spelling
- **When** the check runs
- **Then** the line reports it as `new within one refresh` and the exit code is 0
- **Test:** tests/test_engine_registry.py::test_first_seen_warn_stays_report_only

#### Scenario: A declared refusal is settled and never repeats

- **Given** an old dated capture naming an engine whose repo is listed in
  `NON_ENGINE_REPOS` (`deepseek-ai/deepseek-harness`)
- **When** the check runs with `--now` 290 days after the capture
- **Then** the decision reports OK as a declared refusal, no REPEAT line is
  printed, and the exit code is 0
- **Test:** tests/test_engine_registry.py::test_declined_engine_never_counts_as_repeat

#### Scenario: A fresh capture cannot launder an old spelling's age

- **Given** the same unregistered spelling named in a capture dated 10 days
  before `--now` AND in one dated 1 day before `--now`
- **When** the check runs
- **Then** the first-seen date reported is the OLDER capture and the verdict is
  a REPEAT (exit 1)
- **Test:** tests/test_engine_registry.py::test_oldest_dated_capture_decides_first_seen

#### Scenario: The shipped raw history carries no unresolved repeat

- **Given** `data/raw` and `data/models.json` as shipped in the tree
- **When** `make engine-check` runs with no `--now` override
- **Then** the exit code is 0 and no REPEAT line is printed
- **Test:** tests/test_engine_registry.py::test_shipped_raw_has_no_stale_warn

#### Scenario: Undated captures report age as unknown, never as a repeat

- **Given** a fixture raw file whose filename carries no date naming unregistered
  engines
- **When** the CLI branch test runs the check over it
- **Then** every WARN names `first seen unknown` and the exit code is 0
- **Test:** tests/test_engine_registry.py::test_engine_check_cli_every_branch
