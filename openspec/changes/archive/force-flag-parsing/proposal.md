# Proposal: force-flag-parsing

Issue: #227 — `tech-debt: FORCE=0 forces: any non-empty value is truthy to make`

## Why

`parse_bool` was written for exactly this class (#227), and `decide` uses it — but the
call site that performs the destructive act never got the value:

- `Makefile:236` is `python3 scripts/ensure_image.py publish $(if $(FORCE),--force,)`.
  GNU make's `$(if …)` tests only whether `FORCE` is NON-EMPTY, so `FORCE=0`,
  `FORCE=false` and `FORCE=no` all render the same bare `--force`, and
  `publish(force="--force" in argv[2:])` reads that as ON — the off value takes the
  destructive branch and rebuilds + republishes the fleet's base image.
- The same bare flag is an outright crash on the other action: `decide --force`
  reaches `opt("--force", "false")`, which does `argv[argv.index("--force") + 1]`
  and raises `IndexError: list index out of range` (measured on `master` `cc06fcf`).

So the strictness lives in `parse_bool` and is bypassed by both the Makefile's
argument shape and the two argument parsers.

## What Changes

- **`scripts/ensure_image.py` gains ONE parser**, `force_flag(argv)`, used by BOTH
  `publish` and `decide`: `--force=<bool>`, `--force <bool>` and a bare `--force`
  (meaning ON) are accepted; every value goes through `parse_bool`, so `--force 0` is
  OFF, `--force ''` is OFF and `--force maybe` fails loudly.
- **`Makefile`'s `publish-agent-image` forwards the VALUE** (`--force=$(FORCE)`), so
  `FORCE=0` reaches the script as off instead of being flattened to a flag.
- **`tests/test_ensure_image.py::test_force_reaches_the_script_as_a_value_not_a_bare_flag`**
  drives the real `publish`/`decide` entry points in every spelling, and asserts the
  Makefile target itself carries the value.

Verified RED against the pre-change `Makefile` + `scripts/ensure_image.py` (4 checks:
`--force 0` rebuilds, `--force=1` is not recognised, `decide --force` dies, the
Makefile drops the value), GREEN after.

## Impact

`scripts/ensure_image.py`, `Makefile` (one recipe), `tests/test_ensure_image.py`, this
OpenSpec change and the regenerated `OPENSPEC.md`. No new target, stage, workflow job
or image, so `ARCHITECTURE.md` is unchanged (rule 6h).

## Not covered

- **`rebuild-decision`'s own shape** (`--force "$(if $(FORCE),$(FORCE),false)"`): it
  already forwards the value and keeps working; making it use `--force=` too is
  cosmetic and would churn a test helper.
- **A `FORCE` value that is neither on nor off** (`maybe`): `parse_bool` refuses it and
  the job fails — that is the intended behaviour, not a gap.
