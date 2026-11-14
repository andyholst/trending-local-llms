#!/usr/bin/env python3
"""test_test_runner.py — locks the runner contract from issue #890.

Runs the REAL `scripts/run_tests.sh` against fixture test dirs (external
stand-ins only — the product, the bash runner, always executes, rule 6m) and
proves: a dir with several red modules reports ALL of them in one pass, an
all-green dir exits 0, and the faketime gate (`tests/test_hermes_update_needed.py`)
reports a loud SKIP naming the tool when PATH cannot resolve it — never a
FileNotFoundError traceback.

Run:  python3 tests/test_test_runner.py   or   make test
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "scripts" / "run_tests.sh"

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


def _write(dirp: Path, name: str, body: str) -> None:
    (dirp / name).write_text(body)


def _run_runner(dirp: Path) -> tuple[int, str]:
    r = subprocess.run(
        ["bash", str(RUNNER), str(dirp)],
        capture_output=True, text=True, timeout=600,
    )
    return r.returncode, r.stdout + r.stderr


def test_the_runner_reports_every_red_in_one_pass() -> None:
    """Two red modules: BOTH are shown and BOTH are named, in one invocation."""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _write(d, "test_a_ok.py", "print('ok a')\n")
        _write(d, "test_b_red.py", "print('b blew up')\nraise SystemExit(1)\n")
        _write(d, "test_c_ok.py", "print('ok c')\n")
        _write(d, "test_d_red.py", "print('d blew up')\nraise SystemExit(1)\n")
        rc, out = _run_runner(d)
    check("multi-red: exits 1", rc == 1, str(rc))
    check("multi-red: shows the first red module's output", "=== FAIL: test_b_red.py" in out
          and "b blew up" in out, out)
    check("multi-red: does NOT stop there — shows the second red too", "=== FAIL: test_d_red.py" in out
          and "d blew up" in out, out)
    check("multi-red: one summary names BOTH failures",
          "2 FAILED" in out and "test_b_red.py" in out.split("FAILED")[-1]
          and "test_d_red.py" in out.split("FAILED")[-1], out)
    check("multi-red: a stale 'stopping at the first red' line is gone",
          "stopping at the first red" not in out, out)


def test_an_all_green_dir_exits_0() -> None:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _write(d, "test_a_ok.py", "print('ok a')\n")
        _write(d, "test_b_ok.py", "print('ok b')\n")
        rc, out = _run_runner(d)
    check("all-green: exits 0", rc == 0, out)
    check("all-green: every module is counted and announced",
          "2 module(s) passed" in out and "[test] ok test_a_ok.py" in out, out)


def test_the_update_gate_skips_loudly_without_faketime() -> None:
    """PATH that cannot resolve faketime -> exit 0, a SKIP naming the tool, no traceback."""
    with tempfile.TemporaryDirectory() as td:
        empty = Path(td)
        env = dict(os.environ)
        env["PATH"] = str(empty)  # REPLACE PATH (not prepend): nothing resolves
        r = subprocess.run(
            [sys.executable, str(ROOT / "tests" / "test_hermes_update_needed.py")],
            capture_output=True, text=True, timeout=300, cwd=str(ROOT), env=env,
        )
    out = r.stdout + r.stderr
    check("faketime-missing: exits 0 (a loud SKIP, not a red)", r.returncode == 0, out[-400:])
    check("faketime-missing: names the missing tool in a SKIP",
          "SKIP" in out and "faketime" in out, out[-400:])
    check("faketime-missing: no FileNotFoundError traceback", "Traceback" not in out, out[-400:])


def main() -> int:
    print("test runner contract (#890) — real scripts/run_tests.sh against fixture dirs")
    test_the_runner_reports_every_red_in_one_pass()
    test_an_all_green_dir_exits_0()
    test_the_update_gate_skips_loudly_without_faketime()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
