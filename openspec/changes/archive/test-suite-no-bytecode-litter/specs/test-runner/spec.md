# test-runner

## ADDED Requirements

### Requirement: The ONE test runner leaves no bytecode litter in the checkout

`scripts/run_tests.sh` — reached from `make test` only through `_test:`
(rule 6m) — MUST run every module with `PYTHONDONTWRITEBYTECODE=1` exported by
the seam itself, so a green suite writes no `__pycache__` under the tests dir
it runs. Bytecode copies of test modules embed the suite's planted FAKE
credentials and are re-read by every filesystem walker over the checkout —
the exact false-leak source issue #836 measured — so prevention belongs to the
runner, not to whichever gate happens to trip over the litter.

#### Scenario: the runner stays green and leaves no `__pycache__`

- **Given** a scratch tests dir whose probe module imports a sibling helper
  (the mechanism that wrote `tests/__pycache__/wiring.cpython-312.pyc` on the
  host)
- **When** `bash scripts/run_tests.sh <scratch>` runs over it
- **Then** the suite exits 0, the per-module `[test] ok` trace still arrives
  (the issue #911 contract), and no `__pycache__` directory exists anywhere
  under the scratch dir
- **Test:** tests/test_no_bytecode_litter.py::test_the_runner_is_green_and_leaves_no_pycache

#### Scenario: the guard fails on a runner without the flag

- **Given** the same scratch tree run under bare `python3` without
  `PYTHONDONTWRITEBYTECODE`
- **When** the guard's control check runs
- **Then** `__pycache__` IS produced — proving the planted mechanism is real
  and that this guard would go red on the pre-fix runner — and the seam
  itself owns the flag (`export PYTHONDONTWRITEBYTECODE=1` in
  `scripts/run_tests.sh`) so no caller can bypass it
- **Test:** tests/test_no_bytecode_litter.py::test_a_helper_import_under_bare_python3_does_litter
  and tests/test_no_bytecode_litter.py::test_the_seam_owns_the_flag_and_the_only_path
