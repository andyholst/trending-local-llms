## ADDED Requirements

### Requirement: architecture-bot wiring text states the cadence it actually runs

The comment that explains the `architecture-bot` schedule SHALL name the
cadence the pipeline really runs — Wednesday once a week — while keeping the
odd-minute rationale, and no wiring comment or test label SHALL claim an
HOURLY slot while the pinned cron carries a Wednesday day-of-week. A cadence
change must rewrite the prose that explains it, in the same change.

#### Scenario: the shipped comment names the weekly cadence

Given the shipped `.github/workflows/architecture-bot.yml`
When its schedule comment and cron are read together
Then the comment names the Wednesday weekly cadence, keeps the odd-minute
rationale, and no "hourly" claim sits above the Wednesday cron

- **Test:** tests/test_architecture_bot.py::test_the_schedule_comment_names_the_cadence_it_pins

#### Scenario: the old hourly wording fails the guard

Given the pre-change workflow text — "HOURLY, an odd minute (issue #526)"
above `- cron: "13 * * * 3"` (what `git show origin/master` still holds)
When the wiring guard runs against it
Then the guard goes RED naming the misleading claim, not the cron

- **Test:** tests/test_architecture_bot.py::test_the_schedule_comment_names_the_cadence_it_pins

#### Scenario: a green cron assertion with a lying label no longer passes unnoticed

Given `tests/test_architecture_bot.py` asserting the cron list
When the suite runs
Then the label of that assertion states the Wednesday weekly slot, and the
same test enforces the shipped comment against the same cadence

- **Test:** tests/test_architecture_bot.py::test_the_schedule_comment_names_the_cadence_it_pins
