# One reader for the stage map

**Issue:** [#514](https://github.com/andyholst/trending-local-llms/issues/514)
**Capability:** `stage-wiring`

## Why

The rule "every registered validator stage is selected by a `--only` list in the Makefile" existed
**twice**: `tests/test_validate.py` re-parsed the Makefile with its own regex
(`--only\s+([\w,]+)`), while `scripts/architecture_check.py` implements the same rule by AST
(`validate_stages`, `stage_lists`) as a guard in `make architecture-check`.

Two readers of one contract drift silently: a Makefile shape one regex accepts (a `--only` written
with `=`, a continuation line) turns one red while the other stays green, and neither answer can be
trusted.

## What Changes

- **`tests/test_validate.py`** imports `architecture_check.stage_lists` and
  `validate_stages` instead of parsing the Makefile itself, and gains an assertion that the two
  readers **agree** on the registered stage set — so a change to the validator's registrations can
  never be read differently by the test and the guard.
- The vacuous check I first wrote (comparing the reader's output with itself) is replaced by one
  that proves the reader actually found the lists.

## Impact

One implementation decides what "a stage is wired" means; the test calls it. A future Makefile
shape cannot make the test and `make architecture-check` disagree.

## Not covered (out of scope)

- `stage_lists` still reads targets and stages with regexes over the Makefile text; it is ONE reader,
  not a parser. Filed as a finding with the shape a real parse would take.
