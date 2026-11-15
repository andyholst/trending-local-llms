# Proposal: test-suite-no-bytecode-litter

Issue: #839 — "make test litters the checkout with Python bytecode copies of
PR: #1060
its credential fixtures"

## Why

The host's `make test` leaves `tests/__pycache__/*.pyc` behind — bytecode
copies of test modules that embed the suite's planted FAKE credentials
(measured: `wiring.cpython-312.pyc`, `test_secret_scan.cpython-312.pyc`).
Those copies were the exact false-leak source issue #836 filed:
`make secret-scan` went red on a `.pyc` no commit could ever carry. #836
fixed the SCAN side (the verdict classifies by what git could commit); the
LITTERING side remained: every filesystem walker over the checkout
(secret-scan today, security scans or any future byte-level gate) re-reads
bytecode copies of fixture secrets, and the checkout keeps growing junk no
gate wants.

## What Changes

- `scripts/run_tests.sh` — the ONE test runner — exports
  `PYTHONDONTWRITEBYTECODE=1`, so every caller (container `_test:`, host,
  direct invocation) runs the suite without writing bytecode.
- `tests/test_no_bytecode_litter.py` — a guard that proves the contract
  end to end with the REAL runner over a scratch tree whose probe module
  IMPORTS a sibling helper (the exact mechanism that wrote
  `tests/__pycache__/wiring.cpython-312.pyc`): a control run under bare
  `python3` DOES litter (the guard fails on the pre-fix runner), and the
  runner run is green, keeps the `[test] ok` trace (issue #911), and leaves
  zero `__pycache__` under the tests dir.

## Impact

- Capability: `test-runner`
- Spec delta: `specs/test-runner/spec.md`
- Tests: `tests/test_no_bytecode_litter.py` (new module, auto-discovered by
  the runner)
- Data: none. Pipeline/data contracts: none.

## Not covered

- Cleaning the `__pycache__` litter ALREADY present in human checkouts is a
  host-side act (junk, gitignored); no gate here deletes files from trees it
  does not own.
- `PYTHONDONTWRITEBYTECODE=1` in the runner covers every suite entry; no
  other Makefile recipe is involved (rule 6m: `make test` → `_test:` →
  `scripts/run_tests.sh` is already the only path).
