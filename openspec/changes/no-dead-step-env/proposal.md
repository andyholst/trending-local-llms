# A step setting lives in one place

**Issue:** [#489](https://github.com/andyholst/trending-local-llms/issues/489)
**Capability:** `bot-alarm-configuration`

## Why

`.github/workflows/pr-health.yml` set `MAX_FIXBOT_COMMITS: "2"` at a step's `env:` **while the same
step ran** `make pr-health … MAX_FIXBOT_COMMITS=2`. The env entry changed nothing; the NEXT step
(`COMMENT=1`) had no such entry, which is exactly why it received an **empty** value and crashed
(run 39530945300). Reading the YAML the two steps looked configured the same way — the difference
that caused the failure was invisible.

A setting declared twice is read as authoritative in the place that does nothing, so a reader — or an
agent fixing the crash — has to discover the override by running it. Rule 6d's one-implementation
argument applies to configuration too.

## What Changes

- **`tests/test_workflows.py`** — `test_a_step_setting_lives_in_env_or_on_the_command_line_never_both`
  scans every step of every workflow: an `env:` key that the SAME step's `run:` assigns a
  **different** value is reported, naming the step and the override.
  - Passing the env value through (`REPO="$REPO"`) is **not** an override: the step still has one
    source, which is the idiomatic shape this repo uses everywhere.
- **`.github/workflows/pr-health.yml`** — the dead `MAX_FIXBOT_COMMITS:` entry is removed, with a
  comment saying why the command line carries it alone.

## Impact

The measured case is fixed and the shape is refused. A future step cannot declare a setting twice
and look configured while ignoring one of the copies.

## Not covered (out of scope)

- The rule reads the YAML of each step, so an override performed by `export KEY=…` inside a `run:`
  block is not seen. Filed as a finding with the shell-parsing shape it needs.
