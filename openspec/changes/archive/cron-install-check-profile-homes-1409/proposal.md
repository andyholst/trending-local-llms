# Proposal: cron-install-check-profile-homes-1409

Issue: #1409
PR: #1421

## Why

`make cron-install-check` (#1272) only worked when `HERMES_HOME` already pointed at the profile: it defaulted `--jobs` to `$HERMES_HOME/cron/jobs.json` (else `~/.hermes/cron/jobs.json`) and `--wrappers` to `~/.hermes/scripts/`. On a host running the fleet under a NAMED PROFILE both live under `~/.hermes/profiles/<profile>/`, so a clean shell died before inspecting anything:

```
$ env -u HERMES_HOME -u HERMES_SESSION_PROFILE make cron-install-check
[cron-install] FAIL cannot read cron jobs: FileNotFoundError
```

Measured on asimov@mac: `~/.hermes/cron/jobs.json` does not exist; the jobs are at `~/.hermes/profiles/tll-planner/cron/jobs.json` and `~/.hermes/profiles/project-manager/cron/jobs.json`, while `~/.hermes/profiles/orchestrator/cron/jobs.json` exists with 0 jobs. The gate that exists to prove "both hosts have the two-job trigger" could not be run from a plain shell on either host.

## What Changes

- `scripts/cron_install_check.py` discovers the jobs file across the Hermes homes instead of assuming one: `$HERMES_HOME/cron/jobs.json`, then `~/.hermes/cron/jobs.json`, then each `~/.hermes/profiles/*/cron/jobs.json` in sorted order. The first candidate that actually CARRIES jobs wins; an empty `{"jobs": []}` profile is skipped so an idle profile cannot shadow the profile that runs the fleet.
- The wrappers directory is the matching home's `scripts/`. The explicit `--jobs` / `--wrappers` overrides keep working unchanged.
- A host with no jobs file anywhere now fails with the existing `expected exactly 1 no-agent watchdog job, found 0` refusal — never a traceback.
- `tests/test_cron_install_check.py` covers the discovery order, the empty-file skip, the clean no-jobs failure and the overrides.

## Impact

No contract, schema, workflow or data change. Every refusal #1272 lists is unchanged; the check still makes no network call and reads no credential value. The Makefile target, the detector and the host installations are untouched.

## Not covered

- No new cron job and no GitHub Actions schedule.
- `HERMES_SESSION_PROFILE` is not consulted: the discovery order is the one the issue names.
