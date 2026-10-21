# env-int-empty-is-missing

## ADDED Requirements

### Requirement: An empty setting is a missing setting

Reading a numeric setting from the environment MUST treat an unset value and a
set-but-blank value the same way: both yield the documented default. A value that is
present and not a number MUST fail loudly, naming the variable and what it held, so a
typo is never silently read as the default. This is one implementation
(`scripts/env_int.py`), used by every script that reads a number from the environment.

#### Scenario: the measured empty value stops crashing the sweep

- **Given** the environment `MAX_FIXBOT_COMMITS=` (set, empty) and the real `make pr-health REPO=x/y COMMENT=1`
- **When** the target runs with a stub `gh` for the network
- **Then** it exits 0, prints its `[pr-health] …` report, and no traceback appears
- **Test:** `tests/test_pr_health.py::test_the_real_target_survives_an_empty_max`

#### Scenario: unset, empty and whitespace all mean the default

- **Given** a setting name that is unset, then `""`, then `"   "`, then `"3"`, then `" 3 "`
- **When** `env_int(name, 2)` is called
- **Then** the results are 2, 2, 2, 3 and 3
- **Test:** `tests/test_pr_health.py::test_an_empty_setting_means_missing`

#### Scenario: a non-numeric setting stays loud

- **Given** `MAX_FIXBOT_COMMITS=abc` (or `PH_TEST_INT=2.5` for the helper)
- **When** the target (or the helper) runs
- **Then** it fails, naming the variable and stating it is not a number
- **Test:** `tests/test_pr_health.py::test_the_real_target_survives_an_empty_max`

### Requirement: The wrapper never manufactures an empty value

The public `pr-health` target MUST forward `MAX_FIXBOT_COMMITS` only when it is set,
so a `COMMENT=1` call cannot export a zero-length value into the recipe's environment.

#### Scenario: the forwarding is conditional

- **Given** the shipped Makefile
- **When** the `pr-health` target is read
- **Then** it carries no unconditional `MAX_FIXBOT_COMMITS="$(MAX_FIXBOT_COMMITS)"` assignment
- **Test:** `tests/test_pr_health.py::test_sweep_never_exports_an_empty_setting`

### Requirement: No second reading of a number from the environment

A script MUST NOT read an integer or float straight out of the environment; a new
`int(os.environ…)` anywhere under `scripts/` is a failure, because it reintroduces
the class this change exists to remove.

#### Scenario: a reintroduced bare read fails the suite

- **Given** every file in `scripts/` except `env_int.py`
- **When** the guard scans them for `int(os.environ` / `float(os.environ`
- **Then** it finds none
- **Test:** `tests/test_pr_health.py::test_no_script_reads_a_number_straight_from_the_environment`
