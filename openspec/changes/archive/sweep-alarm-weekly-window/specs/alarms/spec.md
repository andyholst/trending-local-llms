## ADDED Requirements

### Requirement: The sweep alarm's staleness window is the weekly sweep's own cadence

The window the sweep alarm measures against is decided ONCE, by
`scripts/sweep_alarm.py`'s `--max-age-hours` default (168 h). The Makefile
recipe forwards the flag only when the caller supplies `MAX_AGE_HOURS`, and
no pipeline hardcodes a window shorter than the weekly cadence — an
hourly-era literal guarantees a red on the normal schedule and buries the
drop this alarm exists to catch.

#### Scenario: the script's default is a week

- **Given** `scripts/sweep_alarm.py`'s argument parser
- **When** the wiring test reads `--max-age-hours`'s default and its help text
- **Then** the default is 168 h and the help names it
- **Test:** tests/test_sweep_alarm.py::test_the_window_default_is_the_weekly_sweep

#### Scenario: no wiring hardcodes an hourly-era window

- **Given** the `sweep-alarm` recipe in the `Makefile` and the sweep-alarm step of
  `.github/workflows/queued-alarm.yml`
- **When** the wiring test reads both
- **Then** the recipe passes `--max-age-hours` only under `$(if $(MAX_AGE_HOURS),…)`
  and the workflow step carries no `MAX_AGE_HOURS` literal for `sweep-alarm`
- **Test:** tests/test_sweep_alarm.py::test_no_wiring_hardcodes_an_hourly_era_window
