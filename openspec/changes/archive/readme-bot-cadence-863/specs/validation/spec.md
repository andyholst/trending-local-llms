## ADDED Requirements

### Requirement: The generated README's bot-cadence prose matches the pinned crons

The generated README SHALL describe every scheduled pipeline with its pinned
cadence (once a week, Wednesday) and SHALL NOT claim an hourly cadence, a
non-Wednesday weekday, or a cron expression the named workflow does not
schedule. `scripts/validate.py` SHALL fail the readme stage when such a claim
appears on a line naming a scheduled pipeline.

#### Scenario: An hourly claim on a pipeline line is refused

- **Given** a fixture README line naming `issue-review-bot.yml` and claiming it "runs hourly"
- **When** `check_readme_bot_cadence` runs
- **Then** the run records a `readme-bot-cadence` failure naming the line and the pipeline
- **Test:** tests/test_readme_bot_cadence.py::test_hourly_claim_is_refused

#### Scenario: A "twice an hour" claim is refused

- **Given** a fixture README line naming `queued-alarm.yml` with "twice an hour at `:07`/`:37`"
- **When** `check_readme_bot_cadence` runs
- **Then** the run records the cadence failure
- **Test:** tests/test_readme_bot_cadence.py::test_per_hour_claim_is_refused

#### Scenario: A wrong weekday is refused

- **Given** a fixture README line naming `code-review-bot.yml` with "weekly Monday"
- **When** `check_readme_bot_cadence` runs
- **Then** the run records the weekday failure
- **Test:** tests/test_readme_bot_cadence.py::test_wrong_weekday_is_refused

#### Scenario: A quoted cron must be one the workflow schedules

- **Given** a fixture README line quoting `41 * * * 4` for `issue-review-bot.yml`, whose real schedule is `41 * * * 3`
- **When** `check_readme_bot_cadence` runs
- **Then** the run records the cron cross-check failure
- **Test:** tests/test_readme_bot_cadence.py::test_quoted_cron_must_match_the_workflow

#### Scenario: A true weekly line passes

- **Given** a fixture README naming the reviewer and the sweep with their real Wednesday crons
- **When** `check_readme_bot_cadence` runs
- **Then** no failure is recorded
- **Test:** tests/test_readme_bot_cadence.py::test_a_true_weekly_line_passes

#### Scenario: The real README and template are clean

- **Given** this repository after the template fix and `make render-readme`
- **When** the check runs against the real `README.md`, and the template is scanned for the retired claims
- **Then** the check passes and the template holds no "per hour" / "twice an hour" / "weekly Monday `07:23`" bot claim
- **Test:** tests/test_readme_bot_cadence.py::test_real_repo_readme_is_clean
