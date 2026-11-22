#!/usr/bin/env python3
"""ONE pytest plugin so plain `pytest` agrees with `make test` (issue #1301).

Every `tests/test_*.py` is a SCRIPT: `scripts/run_tests.sh` runs each module in its own
process, and the module's own `check()` counter is what `main()` turns into an exit code.
A developer (or an agent) who verifies with plain `pytest` instead gets a DIFFERENT
verdict, because pytest collects the `test_*` functions and never calls `main()` — so a
module whose `check()` calls all failed still reports `N passed`:

    $ python3 tests/test_agent_image_smoke.py     -> FAILED 19 | FAILED 2   (rc 1)
    $ python3 -m pytest tests/test_agent_image_smoke.py -q -> 5 passed      (rc 0)

That is how a red gate gets pushed as "verified" (#1301 was filed from exactly this: run
45029201948). The two verdicts must not be able to disagree.

This plugin is the seam. It is loaded by pytest's own autoload (a top-level module named
`pytest_*.py` on `sys.path`, no `conftest.py` and no config file needed), and it:

  * wraps each collected module's `check()` so the module's failure counter is read AFTER
    every test function runs, and
  * fails the session (`exitstatus = 1`) naming the modules whose counter is non-zero.

It changes nothing for the seam itself: `scripts/run_tests.sh` never imports pytest, so
`make test` still runs each module as a script and its verdict is unchanged.

Usage (plain pytest, from the repo root):

    python3 -m pytest tests/            # now red when a module's check() failed
    python3 -m pytest tests/test_ci_wiring.py

Deliberate limits:
  * Only modules that define a callable `check` are wrapped. A module with no `check()`
    (or one whose counter is not a module global named in `COUNTER_NAMES`) is reported
    by `--check-parity-report` rather than silently skipped.
  * A module whose import raises `SystemExit` (the "SKIP: dependency missing" house
    shape, e.g. `tests/test_workflows.py` without PyYAML) is left alone — pytest's own
    collection error for it is the honest outcome.
  * The counter is read, never written: this plugin does not add or reset checks, it
    only observes the module's own accounting.

Usage as a module:

    python3 scripts/check_counter_parity.py --root .          # report, exit 1 on drift
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

#: The module-level counter a `check()` increments on a failure. The house shape is
#: `_FAIL`; the tree also spells it `FAILED`, `_failed`, `_checks_failed`, `passed`/`failed`
#: (two modules) and one module (`tests/test_no_bytecode_litter.py`) appends to a list.
#: Read only — this plugin never assigns to them.
COUNTER_NAMES = ("_FAIL", "FAILED", "FAILURES", "_failed", "_checks_failed", "failed")

#: A module-level `0` (or `[]`) assignment to one of the counter names, including the
#: chained spelling `PASSED = FAILED = 0` / `passed = failed = 0` and a type annotation
#: (`FAILED: list[str] = []`).
_HAS_COUNTER = re.compile(
    r"^(?:[A-Za-z_][A-Za-z0-9_]*\s*=\s*)*(" + "|".join(COUNTER_NAMES) + r")"
    r"(?:\s*:\s*[A-Za-z_.\[\]]+)?\s*=\s*(?:0|\[\])\s*$",
    re.M,
)
_HAS_CHECK = re.compile(r"^def check\s*\(", re.M)

#: `tests/test_fleet_lifecycle.py`'s `check(cond, msg) -> int` returns 1 on a failure and
#: keeps no module counter, so it cannot be observed by reading a global. Its module is
#: still covered by the pytest verdict (its `test_*` functions run and a raised assertion
#: fails the session) — naming it here keeps the report honest instead of silently skipping.
RETURN_COUNTER_MODULES = ("test_fleet_lifecycle.py",)


def module_qualifies(text: str) -> bool:
    """True when the module's own accounting can be observed here."""
    return bool(_HAS_CHECK.search(text)) and bool(_HAS_COUNTER.search(text))


def counters_of(text: str) -> tuple[str, ...]:
    """The counter names this module declares, in declaration order.

    Handles the chained spelling (`PASSED = FAILED = 0`) and the typed list
    (`FAILED: list[str] = []`) as well as the plain `_FAIL = 0`.
    """
    found: list[str] = []
    for name in COUNTER_NAMES:
        if re.search(rf"(?:^|[=\s]){name}(?:\s*:\s*[A-Za-z_.\[\]]+)?\s*=\s*(?:0|\[\])", text, re.M):
            found.append(name)
    return tuple(found)


# --------------------------------------------------------------------------- pytest


class _Parity:
    """Wrap collected modules' `check()` and fail the session on a non-zero counter."""

    def __init__(self) -> None:
        # module name -> (wrapped check, counter names)
        self.hooked: dict[str, tuple[object, tuple[str, ...]]] = {}
        self.skipped: dict[str, str] = {}

    def observe(self, item) -> None:
        module = getattr(item, "module", None)
        if module is None:
            return
        name = getattr(module, "__name__", "")
        if name in self.hooked or name in self.skipped:
            return
        original = getattr(module, "check", None)
        if not callable(original):
            return
        source = _source_of(module)
        if source is None:
            self.skipped[name] = "no source file"
            return
        counters = counters_of(source)
        if not counters:
            self.skipped[name] = "no module-level failure counter"
            return
        state = {"seen": 0}

        def check(*args, **kwargs):
            result = original(*args, **kwargs)
            state["seen"] += 1
            # A `check()` that RETURNS its verdict (test_fleet_lifecycle's
            # `check(cond, msg) -> int`) has no counter to read after the fact, so the
            # wrapper is where the failure must become a real assertion.
            if isinstance(result, int) and result:
                raise AssertionError(
                    f"[check-parity] {name}: check() returned {result} under plain pytest"
                )
            return result

        module.check = check
        self.hooked[name] = (state, counters)

    def verdict(self) -> tuple[list[str], dict[str, str]]:
        """(modules whose counter is non-zero, modules that could not be observed)."""
        failed: list[str] = []
        for name, (state, counters) in sorted(self.hooked.items()):
            module = sys.modules.get(name)
            if module is None:
                continue
            values: dict[str, int] = {}
            for counter in counters:
                value = getattr(module, counter, 0)
                # A list counter (FAILED.append) counts its length; anything else
                # that is not an int reads as 0 rather than crashing the session.
                if isinstance(value, (list, tuple)):
                    values[counter] = len(value)
                elif isinstance(value, int):
                    values[counter] = value
                else:
                    values[counter] = 0
            if any(values.values()):
                failed.append(f"{name} ({', '.join(f'{k}={v}' for k, v in values.items() if v)})")
        return failed, dict(sorted(self.skipped.items()))


_PLUGIN = _Parity()


def _source_of(module) -> str | None:
    """The module's source text, read from its file (never executed)."""
    path = getattr(module, "__file__", None)
    if not path:
        return None
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def pytest_itemcollected(item) -> None:
    """pytest hook: observe each collected module once, before its tests run."""
    _PLUGIN.observe(item)


def pytest_sessionfinish(session, exitstatus: int) -> None:
    """pytest hook: the session is red when a module's own counter says it failed."""
    failed, skipped = _PLUGIN.verdict()
    if skipped:
        listed = ", ".join(f"{name}: {why}" for name, why in skipped.items())
        print(f"[check-parity] not observed (no check() counter): {listed}")
    if failed:
        print("[check-parity] FAIL: these modules' own check() counter is non-zero "
              "under plain pytest (run them as scripts to see the FAIL lines):")
        for entry in failed:
            print(f"[check-parity]   {entry}")
        session.exitstatus = 1


# --------------------------------------------------------------------------- report


def scan(root: Path) -> tuple[list[str], list[str]]:
    """(modules whose counter this plugin observes, modules it cannot)."""
    tests = root / "tests"
    if not tests.is_dir():
        print(f"[check-parity] FAIL: {tests} is not a directory — a guard that cannot "
              f"read the tree must not report a clean one", file=sys.stderr)
        raise SystemExit(2)
    qualifies: list[str] = []
    unobserved: list[str] = []
    for path in sorted(tests.glob("test_*.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if module_qualifies(text) or path.name in RETURN_COUNTER_MODULES:
            qualifies.append(path.name)
        else:
            unobserved.append(path.name)
    return qualifies, unobserved


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="repository root (default: cwd)")
    ap.add_argument("--report", action="store_true",
                    help="print the observed/not-observed split and exit on drift")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    qualifies, unobserved = scan(root)
    print(f"[check-parity] {len(qualifies)} module(s) observable via their check() counter")
    if args.report:
        for name in unobserved:
            print(f"[check-parity]   not observed: {name}")
    # Drift = a module that declares check() but no readable counter, because that is
    # exactly the shape whose pytest verdict can disagree with the seam's.
    drift = [n for n in unobserved
             if _HAS_CHECK.search((root / "tests" / n).read_text(encoding="utf-8", errors="replace"))]
    if drift:
        print(f"[check-parity] FAIL: {len(drift)} module(s) define check() with no "
              f"module-level counter, so plain pytest can pass where the seam fails: "
              f"{', '.join(drift)}")
        return 1
    print("[check-parity] OK: every check()-module's counter is observable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
