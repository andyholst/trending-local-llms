"""pytest plugin registration for the check()-counter parity seam (issue #1301).

Every `tests/test_*.py` is a SCRIPT whose verdict is its own `check()` counter, turned
into an exit code by `main()`. Plain `pytest` collects the `test_*` functions and never
calls `main()`, so a module can report `N passed` while the seam says `FAILED`. This
conftest loads `scripts/check_counter_parity.py` — the ONE implementation of the parity
rule — so a plain `pytest` run and `make test` cannot disagree.

Why a conftest and not a `pytest_*.py` next to the tests: pytest only auto-loads a
top-level `pytest_*` module when its directory is on `sys.path`, which depends on the
invoker's cwd (`rootdir` insertion is not guaranteed). A `conftest.py` inside the
directory being collected is loaded by pytest itself, whatever the cwd — measured with a
plugin in a parent directory: silent from `/tmp`, active from the parent.

The runner (`scripts/run_tests.sh`) globs `test_*.py`, so this file is not a test module
and `make test` is unchanged; `scripts/check_pytest_imports.py` scans `test_*.py` only,
so the convention it enforces (no pytest in a test module) is untouched. PyYAML-free and
pytest-free modules that `raise SystemExit(0)` at import still SKIP honestly: pytest
reports the collection error, which is the true outcome, not a masked pass.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

pytest_plugins = ["check_counter_parity"]
