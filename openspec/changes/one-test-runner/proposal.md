# Proposal: one-test-runner

Issues: #176 — `The pytest path in the test image is dead`; #192 — `The _test fallback-chain guard lives in the AMD-backend test file`

## Why

`_test` was:

```make
python3 -m pytest tests/ -q 2>/dev/null || (… 31 explicit `python3 tests/test_*.py` …)
```

`pytest` is **not** installed in `trending-local-llms-test:latest`
(`docker run … python3 -m pytest` → `No module named pytest`), and `2>/dev/null`
threw away the reason. So:

- the intended single entrypoint never ran, and nothing said so;
- the suite that DID run was a hand-maintained list of 31 modules — a test file
  pytest would have collected but nobody appended to the recipe never ran, and a
  collection error (an import failure in a new module) was invisible;
- the one assertion that caught a missing entry lived in `tests/test_amd_backend.py`
  (#192), so a Makefile wiring mistake was reported as an AMD regression and failed
  `validate-mapped`, a stage whose subject is data mapping.

## What Changes

- **`scripts/run_tests.sh` is the ONE runner.** It discovers `tests/test_*.py`, runs
  each in its own process, and **stops at the first red**, printing that module's
  own output. `--list` prints what it would run (the wiring guard uses it); a
  directory with no modules exits 1 rather than reporting a vacuous pass.
- **`_test` is one line**: `bash scripts/run_tests.sh`. The pytest branch is gone, so
  no dead path remains to be mistaken for the suite.
- **`tests/test_ci_wiring.py` owns the wiring**, driven for real against temp
  directories: every `tests/test_*.py` is listed, a failing module fails the run and
  stops it (the module after it does not run), a green directory passes, and an empty
  one is red. The old assertion is removed from `tests/test_amd_backend.py`.
- `ARCHITECTURE.md` describes the new script and the `test` target's new shape.

A new `tests/test_*.py` is therefore wired by construction — the runner globs — and
the guard that proves it lives in a test whose subject IS the wiring.

## Impact

`Makefile` (`_test`), `scripts/run_tests.sh` (new), `tests/test_ci_wiring.py` (new),
`tests/test_amd_backend.py` (one assertion removed), `ARCHITECTURE.md`, this OpenSpec
change and the regenerated `OPENSPEC.md`. No pipeline job or image changes: the base
and test images are untouched (`pytest` is deliberately still absent — the modules are
scripts, not pytest tests).

## Not covered

- **Converting the modules to pytest.** They are script-style (`check()` prints,
  `main()` returns a status); porting ~60 modules is a separate change with no
  behavioural gain, and running them under pytest without an assertion hook would make
  the suite GREEN REGARDLESS of `_FAIL` — strictly worse than what this change does.
- **Parallelising the runner.** Sequential is what the fix loop needs (first red, in
  order); a `-j` mode is a speed change, not a correctness one.
