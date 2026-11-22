# Proposal: check-counter-parity-1301

Issue: #1301

## Why

Every `tests/test_*.py` is a SCRIPT whose verdict is its own `check()` counter, turned into an exit code by `main()` and executed per-process by `scripts/run_tests.sh`. Plain `pytest` collects the `test_*` functions and never calls `main()`, so the two verdicts can disagree on the same bytes: measured on the pre-fix head, `python3 tests/test_agent_image_smoke.py` printed `FAILED 19 | FAILED 2` (rc 1) while `python3 -m pytest tests/test_agent_image_smoke.py -q` reported `5 passed` (rc 0). A developer or agent that verifies with plain pytest therefore gets a green result for a module the repo's own runner calls red — the exact shape that let a red gate be pushed as "verified" (run 45029201948).

## What Changes

- Add `scripts/check_counter_parity.py`: the ONE implementation of the parity rule. It wraps a collected module's `check()` and reads the module's own failure counter after its tests run; a non-zero counter fails the pytest session naming the module and the counter value.
- Add `tests/conftest.py` registering that module through `pytest_plugins`, so plain `pytest` loads it whatever the cwd (a top-level `pytest_*.py` is only auto-loaded when its directory is on `sys.path`).
- Add the Makefile target `check-counter-parity` (internal `_check-counter-parity`) and bundle it into `make lint`: a `check()`-module with no readable counter is the drift that lets the verdicts disagree.
- Add `tests/test_check_counter_parity.py`: the tree-wide detector half always runs, and the real-pytest half (a scratch module with a failing `check()`) runs where pytest exists, declaring the gap through the #1154 seam where it does not.

## Impact

`make test` is unchanged: `scripts/run_tests.sh` globs `test_*.py`, so `conftest.py` is not a test module, and it never imports pytest. `scripts/check_pytest_imports.py` scans `test_*.py` only, so the no-pytest convention in test modules is untouched. No contract, data format, image or workflow wiring change.

## Not covered

- No change to any existing test module's `check()` convention (149 modules) — the seam observes the counters that already exist, it does not rewrite them.
- No pytest dependency added to the TEST image, and no `import pytest` in any `tests/test_*.py` (issue #768 stays intact).
- No CI dispatch, no merge, no master push, no collaborator grant.
