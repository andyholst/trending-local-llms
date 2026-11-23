## ADDED Requirements

### Requirement: The jobs file is discovered across the Hermes homes

`scripts/cron_install_check.py` SHALL locate the cron jobs file by trying `$HERMES_HOME/cron/jobs.json`, then `~/.hermes/cron/jobs.json`, then each `~/.hermes/profiles/*/cron/jobs.json` in sorted order. The first candidate that carries at least one job SHALL be used, and an empty jobs file SHALL be skipped so an idle profile cannot shadow the profile that runs the fleet. The wrappers directory SHALL be the matching home's `scripts/`.

#### Scenario: A named-profile host in a clean shell

- **Given** a host with no `~/.hermes/cron/jobs.json` and a profile home carrying the two-job install
- **When** `env -u HERMES_HOME -u HERMES_SESSION_PROFILE make cron-install-check` runs
- **Then** it prints `[cron-install] OK 2 job(s)` and exits 0
- **Test:** tests/test_cron_install_check.py::test_clean_shell_discovers_the_profile_install

#### Scenario: An empty profile does not shadow the fleet profile

- **Given** a sorted-first profile whose `cron/jobs.json` is `{"jobs": []}` and a later profile carrying the two jobs
- **When** the jobs file is discovered
- **Then** the later profile's jobs file is the one read
- **Test:** tests/test_cron_install_check.py::test_discovery_skips_an_empty_jobs_file

#### Scenario: The search order is stable

- **Given** `$HERMES_HOME`, `~/.hermes` and two profile homes
- **When** the homes are enumerated
- **Then** `$HERMES_HOME` comes first and is never repeated, then `~/.hermes`, then the profiles sorted by name
- **Test:** tests/test_cron_install_check.py::test_hermes_homes_order

### Requirement: A host with no jobs fails cleanly, and the overrides still work

With no jobs file carrying a job anywhere, the check SHALL report the existing `expected exactly 1 no-agent watchdog job, found 0` refusal and exit non-zero — never a traceback. The explicit `--jobs` and `--wrappers` overrides SHALL keep their exact old meaning.

#### Scenario: A host with no jobs

- **Given** a Hermes home with no jobs file at all
- **When** `make cron-install-check` runs
- **Then** it exits 1 naming the missing watchdog and prints no `FileNotFoundError` or traceback
- **Test:** tests/test_cron_install_check.py::test_host_with_no_jobs_fails_cleanly

#### Scenario: Explicit overrides

- **Given** an explicit `--jobs` and `--wrappers` pointing at a fixture install
- **When** the check runs
- **Then** it prints `[cron-install] OK 2 job(s)` and exits 0
- **Test:** tests/test_cron_install_check.py::test_explicit_overrides_still_work

#### Scenario: An explicit jobs path that does not exist

- **Given** `--jobs` naming a missing file
- **When** the check runs
- **Then** it prints the existing `cannot read cron jobs: FileNotFoundError` refusal and no traceback
- **Test:** tests/test_cron_install_check.py::test_explicit_missing_jobs_is_a_clean_failure
