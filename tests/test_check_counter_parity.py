#!/usr/bin/env python3
"""test_check_counter_parity.py — issue #1301: plain pytest must not out-green the seam.

Every `tests/test_*.py` is a SCRIPT whose verdict is its own `check()` counter, and
`scripts/run_tests.sh` is what turns that into a red `make test`. A developer (or an agent)
who verifies with plain `pytest` instead gets a DIFFERENT verdict, because pytest collects
the `test_*` functions and never calls `main()`:

    $ python3 tests/test_agent_image_smoke.py          -> FAILED 22 | FAILED 1   (rc 1)
    $ python3 -m pytest tests/test_agent_image_smoke.py -> 5 passed            (rc 0)

This suite locks the parity seam (`scripts/check_counter_parity.py` + `tests/conftest.py`)
with the REAL pytest as the external system (rule 6m): a scratch module is planted with a
`check()` that FAILS, and the guard proves plain pytest now exits 1 naming the module. The
pre-seam behaviour (exit 0 over a failing counter) is asserted too, so the guard is RED on
the code it locks.

When pytest is absent (the host `make test` image deliberately ships none, and this host has
no pytest), the pytest half is declared through the #1154 seam and the pure detector half
still runs — a bare SKIP is a refusal (issue #1171/#1173).

Run:  python3 tests/test_check_counter_parity.py   or   make test
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import coverage_gap  # noqa: E402

try:
    import check_counter_parity as CCP  # noqa: E402
except ImportError:  # the pre-change tree: the guard must RED loudly, not traceback
    CCP = None  # type: ignore[assignment]

_PASS = 0
_FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"ok   {name}")
    else:
        _FAIL += 1
        print(f"FAIL {name}")
        if detail:
            print(detail)


#: A module in the house shape: a `check()` counter and a `test_*` function that calls it.
PLANT = '''\
_PASS = 0
_FAIL = 0


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def test_wiring():
    check("planted failure", False, "issue #1301")


def main():
    return 1 if _FAIL else 0
'''


def _pytest(root: Path) -> str:
    """The pytest invocation: a real interpreter that HAS pytest, if this identity does."""
    for candidate in (sys.executable, shutil.which("python3") or "", "python3"):
        if not candidate:
            continue
        probe = subprocess.run([candidate, "-c", "import pytest"], capture_output=True)
        if probe.returncode == 0:
            return candidate
    return ""


#: The probe binary this half needs. A synthetic name (it ships nowhere) so the declared
#: line is the same in every identity — the #1171 lesson: probing a REAL binary by name
#: makes the verdict depend on WHERE the module runs rather than on the contract.
PYTEST_PROBE = "pytest-capable-python"


def test_the_detector_classifies_the_tree() -> None:
    """The pure half: every check()-module in the repo is observable, none silently skipped."""
    check("the parity seam exists", CCP is not None,
          "scripts/check_counter_parity.py is absent — plain pytest can out-green the seam (#1301)")
    if CCP is None:
        return
    qualifies, unobserved = CCP.scan(ROOT)
    check("the detector sees the tests/ tree", bool(qualifies), f"qualifies={len(qualifies)}")
    drift = [n for n in unobserved
             if CCP._HAS_CHECK.search((ROOT / "tests" / n).read_text(encoding="utf-8",
                                                             errors="replace"))]
    check("no check()-module is unobservable", not drift, f"drift={drift}")
    text = (ROOT / "tests" / "test_agent_image_smoke.py").read_text(encoding="utf-8")
    check("the house shape qualifies", CCP.module_qualifies(text))
    check("the house counter is read", CCP.counters_of(text) == ("_FAIL",),
          str(CCP.counters_of(text)))
    check("the chained spelling is read", CCP.counters_of("PASSED = FAILED = 0\n") == ("FAILED",))
    check("the list spelling is read", CCP.counters_of("FAILURES: list[str] = []\n") == ("FAILURES",))
    check("a module with no counter does not qualify", not CCP.module_qualifies("def check(a, b):\n    pass\n"))


def test_the_plugin_fails_the_session_on_a_failing_counter() -> None:
    """The real half: plain pytest exits 1 over a planted failing check()."""
    interpreter = _pytest(ROOT)
    gap = coverage_gap.external_binary_gap(
        "tests/test_check_counter_parity.py::test_the_plugin_fails_the_session_on_a_failing_counter",
        PYTEST_PROBE,
        "pytest is deliberately absent from the TEST image (#768) and from this host; "
        "the parity half needs a real pytest to execute")
    if gap:
        coverage_gap.announce(gap)
        check("pytest half declared (pytest absent here)", True)
        return
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / "tests").mkdir()
        (tmp / "tests" / "conftest.py").write_text(
            (ROOT / "tests" / "conftest.py").read_text(encoding="utf-8"), encoding="utf-8")
        (tmp / "tests" / "test_planted.py").write_text(PLANT, encoding="utf-8")
        # The planted module FAILS its own check() when run as a script...
        script = subprocess.run([sys.executable, str(tmp / "tests" / "test_planted.py")],
                                capture_output=True, text=True)
        check("the planted module is red as a script (the seam verdict)", script.returncode == 1,
              f"rc={script.returncode}")
        # ...and plain pytest over the SAME bytes must now be red too.
        run = subprocess.run([interpreter, "-m", "pytest", "tests/test_planted.py", "-q"],
                             cwd=str(tmp), capture_output=True, text=True)
        check("plain pytest exits 1 over the failing check() counter", run.returncode == 1,
              f"rc={run.returncode}\n{run.stdout[-500:]}\n{run.stderr[-300:]}")
        check("the plugin names the offending module",
              "test_planted" in run.stdout + run.stderr, run.stdout[-300:])
        check("the plugin carries the counter value",
              "_FAIL=1" in run.stdout + run.stderr, run.stdout[-300:])


def test_the_plugin_is_a_no_op_on_a_clean_module() -> None:
    """A green module stays green — the seam adds no false reds."""
    interpreter = _pytest(ROOT)
    if not interpreter:
        gap = coverage_gap.external_binary_gap(
            "tests/test_check_counter_parity.py::test_the_plugin_is_a_no_op_on_a_clean_module",
            PYTEST_PROBE, "pytest is absent from this identity")
        coverage_gap.announce(gap)
        check("no-op half declared (pytest absent here)", True)
        return
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / "tests").mkdir()
        (tmp / "tests" / "conftest.py").write_text(
            (ROOT / "tests" / "conftest.py").read_text(encoding="utf-8"), encoding="utf-8")
        clean = PLANT.replace('check("planted failure", False, "issue #1301")',
                              'check("planted pass", True)')
        (tmp / "tests" / "test_clean.py").write_text(clean, encoding="utf-8")
        run = subprocess.run([interpreter, "-m", "pytest", "tests/test_clean.py", "-q"],
                             cwd=str(tmp), capture_output=True, text=True)
        check("a clean module is still green under plain pytest", run.returncode == 0,
              f"rc={run.returncode}\n{run.stdout[-300:]}")


def test_wiring() -> None:
    mk = (ROOT / "Makefile").read_text(encoding="utf-8")
    conftest = ROOT / "tests" / "conftest.py"
    check("the conftest registers the ONE plugin", conftest.is_file()
          and "check_counter_parity" in conftest.read_text(encoding="utf-8"))
    check("make test still runs the runner (unchanged)", "_test:\n\tbash scripts/run_tests.sh" in mk)
    check("the runner does not collect conftest as a module",
          "conftest" not in subprocess.run(["bash", str(ROOT / "scripts" / "run_tests.sh"),
                                            "--list"], capture_output=True, text=True).stdout)
    check("the parity target is wired into lint",
          "check-counter-parity" in mk and "_check-counter-parity:" in mk)


def main() -> int:
    print("check()-counter parity (#1301):")
    test_the_detector_classifies_the_tree()
    test_the_plugin_fails_the_session_on_a_failing_counter()
    test_the_plugin_is_a_no_op_on_a_clean_module()
    test_wiring()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
