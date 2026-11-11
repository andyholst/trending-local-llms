#!/usr/bin/env python3
"""Fail when a test module imports or calls the runner the TEST image does not have (issue #768).

Every `tests/test_*.py` is a SCRIPT: `scripts/run_tests.sh` runs each module in its own process,
prints `ok`/`PASS`/`FAIL` lines and exits non-zero on its own failures. The TEST image deliberately
carries NO pytest, so a module that imports it is green on any host and dies inside the TEST image:
measured on qa-validate run 42800200326 (PR #764 head 0db0462), `tests/test_owed_rows.py` carried a
top-level import and the suite died with `ModuleNotFoundError: No module named 'pytest'` after a
~15-minute red `validate` job, while every host gate stayed green.

The convention is documented (the comment beside the Makefile's `_test`, the header of
`scripts/run_tests.sh`); this is the mechanical guard for it, bundled into `make lint` so
qa-validate's `validate` job (and the fix loop, which runs lint first) refuse the violation where
it lives instead of paying for a CI round-trip.

The refused shapes are the provable ones:
  * a top-level `import pytest` / `import pytest.x` / `from pytest import …`
  * a member use of the API: `pytest.` (decorator, fixture, raises, mark, …)
A whole-line comment is not code and is tolerated, so prose may name the runner it forbids. A
dynamic import is not a spelling a lint can see — `make test` in the TEST image stays the backstop.

The house pattern every module follows instead: a fixture-compatible signature with a
`tmp_path=None` fallback (tempfile.mkdtemp) and an explicit `main()` returning the failure exit
code; see any sibling module under `tests/`.

Usage:
    python3 scripts/check_pytest_imports.py [--tests-dir DIR] [PATHS…]

Exit: 0 = clean (or nothing to scan), 1 = violations (file:line named), 2 = the tests dir is missing.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: The import statements and the API member use. `pytest.` covers decorators, fixtures and
#: helpers without needing a name-by-name list of the API.
VIOLATION = re.compile(r"^\s*(?:import\s+pytest\b(?:\s+as\s+\w+)?\b|from\s+pytest\s+import\b)|\bpytest\.")

HOUSE_PATTERN = ("every tests/test_*.py is a SCRIPT run standalone by scripts/run_tests.sh — the "
                 "TEST image has no pytest: use a fixture-compatible signature with a `tmp_path=None` "
                 "fallback (tempfile.mkdtemp) and an explicit `main()` returning the failure exit code")


def scan(path: Path) -> list[int]:
    """The 1-based line numbers of pytest imports / API uses in `path`.

    A whole-line comment is prose, not code, and is tolerated; everything else (code AND strings,
    including docstrings) that matches a refused shape is a finding.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    findings: list[int] = []
    for i, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        if VIOLATION.search(line):
            findings.append(i)
    return findings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fail when a test module imports the absent runner")
    ap.add_argument("--tests-dir", default=str(ROOT / "tests"),
                    help="the tests directory to scan (default: the repo's tests/)")
    ap.add_argument("paths", nargs="*", help="limit the scan to these files (default: every test_*.py in --tests-dir)")
    args = ap.parse_args(argv)
    tests_dir = Path(args.tests_dir)
    if args.paths:
        candidates = [Path(p) for p in args.paths]
    else:
        if not tests_dir.is_dir():
            print(f"[pytest-import-guard] FAIL: {tests_dir} is not a directory — a guard that "
                  f"scans nothing reports a fake clean (#768).", file=sys.stderr)
            return 2
        candidates = sorted(tests_dir.glob("test_*.py"))
    findings: list[tuple[Path, list[int]]] = []
    for path in candidates:
        lines = scan(path)
        if lines:
            findings.append((path, lines))
    if not findings:
        print(f"[pytest-import-guard] OK: no pytest import/use in {len(candidates)} test module(s)")
        return 0
    for path, lines in findings:
        print(f"[pytest-import-guard] FAIL: {path} line(s) {', '.join(str(n) for n in lines[:10])} "
              f"import or call pytest", file=sys.stderr)
    print(f"[pytest-import-guard] {len(findings)} module(s) refuse the standalone-script convention "
          f"(issue #768): {HOUSE_PATTERN}.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
