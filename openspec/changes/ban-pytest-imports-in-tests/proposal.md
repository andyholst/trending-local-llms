# Proposal: ban-pytest-imports-in-tests

Issue: #768 (measured: qa-validate run 42800200326, PR #764 head 0db0462)

## Why

Every `tests/test_*.py` is a SCRIPT: `scripts/run_tests.sh` runs each module in its
own process and the TEST image deliberately carries **no pytest**. `tests/test_owed_rows.py`
imported `pytest` anyway and the violation surfaced only as
`ModuleNotFoundError: No module named 'pytest'` inside the TEST image — after a full
~15-minute red `validate` job — while every host gate (`make lint`, `make architecture-check`,
`make openspec-check`) stayed green. The convention itself is documented (the `Makefile`
comment beside `_test`, the header of `scripts/run_tests.sh`), but nothing enforces it: each
recurrence costs a full CI round-trip plus a repair round before anyone sees it (issue #768).

## What Changes

- **`scripts/check_pytest_imports.py`** — the guard: scans the test modules and fails loudly on a
  top-level `import pytest` / `from pytest import …` or a `pytest.` API use, naming the file, the
  line and the house pattern (fixture-compatible signature with a `tmp_path=None` fallback plus an
  explicit `main()`). Exit 0 clean, 1 with findings, 2 when the tests directory is missing.
- **`make check-pytest-imports`** — the new public target, bundled into the `lint` recipe (rule
  6d), so `qa-validate`'s `validate` job and the fix loop run the guard where the violation lives.
- **`tests/test_pytest_import_guard.py`** — runs the REAL script against planted fixtures
  (rule 6c): a planted `import pytest` fixture goes RED naming file+line, planted
  `from pytest import` and `pytest.` uses go red, a clean tree and a whole-line comment stay
  green, and the REAL `tests/` pass green.
- **Documentation rows**: `ARCHITECTURE.md` §6 lint target table + §6 scripts table, and an
  `AGENTS.md` §8 guard row (the §6 target half is the generated §10 via `make architecture-refresh`).

## Impact

`Makefile` (`lint` recipe + new target), `scripts/check_pytest_imports.py`,
`tests/test_pytest_import_guard.py`, `ARCHITECTURE.md`, `AGENTS.md`, `OPENSPEC.md`.
CI: the guard rides `make lint`, already the FIRST step of `qa-validate`'s `validate` job and the
first check in `scripts/fix_loop.sh` — no new CI job.

## Not covered

- **The arm64 pull gap in `ensure_openspec` (#767)** — it bit this very change locally (a local
  OpenSpec gate needs the `IMAGE_REPO` workaround) and is its own issue with its own fix; it is
  not folded into this change (analysis ships issues, never code).
- **Non-top-level `pytest` spellings** (dynamic `importlib`, string-built imports): the provable
  shapes — the import statements and the `pytest.` API use — are what the guard refuses; a dynamic
  import is not a spelling a lint can see, and `make test` in the TEST image remains the net.
