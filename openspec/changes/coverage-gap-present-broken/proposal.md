# coverage-gap-present-broken — a present-but-broken CLI is a real failure, not a gap

Issue: #1172

## Why

`external_binary_gap` probes with `shutil.which`, so only ABSENCE is declared. A `hermes` that is
on PATH but fails immediately (a stale install, a broken venv, a version mismatch) is not caught:
the module runs the real half and goes red with the CLI's own error. Issue #1172 asks that the two
states never be confused — either the declaration also covers a CLI whose first real invocation
fails, or the guard states explicitly that a present-but-broken binary is a real failure.

## What Changes

- `scripts/coverage_gap.py` gains `external_binary_usable(binary) -> bool` and the named boundary
  `PRESENCE_IS_PRESUMED_USABLE = True`. The seam probes PRESENCE ONLY and never executes the
  binary — running an arbitrary CLI to decide coverage is a side effect at import time, and it
  would move a real failure into the gap class. `external_binary_gap` now reads the probe through
  the one function.
- `tests/test_test_container_identity.py::test_a_present_but_broken_cli_is_a_real_failure_not_a_declared_gap`
  drives the REAL seam in a subprocess with a stub `hermes` that is on PATH and exits 1, and
  drives the REAL `scripts/hermes_skills_register.py` with it: the seam declares NOTHING, and the
  register half exits 2 with the CLI's own message and prints no `[coverage-gap]` line.
- `AGENTS.md` §8: the `tests/test_test_container_identity.py` row carries issue #1172.

## Impact

- No new make target, pipeline job or image; the seam is already bundled into `make test`
  (rule 6d).
- Not covered: making the seam EXECUTE a probe command (the issue's first Done-when branch). It
  is rejected on purpose — a probe that runs an arbitrary CLI at import time is a side effect and
  would launder real failures into coverage gaps.
