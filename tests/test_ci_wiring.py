#!/usr/bin/env python3
"""The test runner's own wiring (issues #176 and #192).

Two failures this exists to catch, both measured:

  * `_test` was `python3 -m pytest tests/ -q 2>/dev/null || (31 explicit calls)`.
    pytest is NOT in the test image, its stderr was thrown away, so the dead
    branch was invisible and the suite that ran was a hand-maintained chain — a
    module pytest would collect but nobody appended never ran.
  * the "every tests/test_*.py is wired" assertion lived in
    `tests/test_amd_backend.py`, so a Makefile wiring mistake was reported as an
    AMD regression and failed a data-mapping stage.

The runner is `scripts/run_tests.sh`; these tests drive it for real (a temp
directory of module scripts, real exit codes — rule 6m, no mocks).

Run:  python3 tests/test_ci_wiring.py   or   make test
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "scripts" / "run_tests.sh"

_PASS = 0
_FAIL = 0


def check(name, cond, detail: object = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def _modules(tmp: Path, failing: str | None = None) -> Path:
    tests = tmp / "tests"
    tests.mkdir()
    for name in ("test_alpha.py", "test_beta.py", "test_gamma.py"):
        body = "print('ran %s')\n" % name
        if name == failing:
            body = "import sys\nprint('FAIL: %s is red')\nsys.exit(1)\n" % name
        (tests / name).write_text(body)
    return tests


def test_the_runner_lists_every_module():
    """A module the runner cannot see is a module that never runs."""
    out = subprocess.run(["bash", str(RUNNER), "--list"], cwd=ROOT, capture_output=True, text=True)
    listed = [Path(line).name for line in out.stdout.split("\n") if line.strip()]
    on_disk = sorted(p.name for p in (ROOT / "tests").glob("test_*.py"))
    check("runner: --list exits 0", out.returncode == 0, out.stderr[:300])
    check("runner: every tests/test_*.py is listed", sorted(listed) == on_disk,
          f"missing={sorted(set(on_disk) - set(listed))} extra={sorted(set(listed) - set(on_disk))}")
    check("runner: no module is listed twice", len(listed) == len(set(listed)), listed)


def test_the_makefile_has_exactly_one_runner_and_no_dead_pytest_branch():
    mk = (ROOT / "Makefile").read_text()
    check("make: _test runs the one runner",
          "_test:\n\tbash scripts/run_tests.sh" in mk, "")
    check("make: the dead pytest branch is gone (pytest is not in the test image)",
          "python3 -m pytest tests/" not in mk, "")


def test_a_failing_module_stops_the_run():
    """The chain must stop at the FIRST red and show that module's own output."""
    tmp = Path(tempfile.mkdtemp())
    try:
        tests = _modules(tmp, failing="test_beta.py")

        # Given a tests directory whose second module fails
        p = subprocess.run(["bash", str(RUNNER), str(tests)], capture_output=True, text=True)

        # Then  the run is red, names the module, and stops there
        check("runner: one red module fails the run", p.returncode == 1, p.stdout + p.stderr)
        check("runner: it names the failing module", "FAIL: test_beta.py" in p.stdout, p.stdout)
        check("runner: it shows the module's own output", "FAIL: test_beta.py is red" in p.stdout, p.stdout)
        check("runner: it stops at the first red", "ran test_gamma.py" not in p.stdout, p.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_a_green_directory_passes():
    tmp = Path(tempfile.mkdtemp())
    try:
        tests = _modules(tmp)
        p = subprocess.run(["bash", str(RUNNER), str(tests)], capture_output=True, text=True)
        check("runner: every module green -> exit 0", p.returncode == 0, p.stdout + p.stderr)
        check("runner: it reports how many ran", "3 module(s) passed" in p.stdout, p.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_an_empty_directory_is_a_failure_not_a_vacuous_pass():
    tmp = Path(tempfile.mkdtemp())
    try:
        tests = tmp / "tests"
        tests.mkdir()
        p = subprocess.run(["bash", str(RUNNER), str(tests)], capture_output=True, text=True)
        check("runner: no modules at all is RED (a suite that runs nothing proves nothing)",
              p.returncode == 1 and "no tests/test_*.py" in (p.stdout + p.stderr), p.stdout + p.stderr)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    print("test runner wiring (issues #176/#192)")
    test_the_runner_lists_every_module()
    test_the_makefile_has_exactly_one_runner_and_no_dead_pytest_branch()
    test_a_failing_module_stops_the_run()
    test_a_green_directory_passes()
    test_an_empty_directory_is_a_failure_not_a_vacuous_pass()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
