#!/usr/bin/env python3
"""Control-flow tests for scripts/fix_loop.sh (the fix-bot repair loop).

The fix-bot never fixed a PR before: its loop ran under `bash -e` (died on the
first red check), never ran `make validate`, never stopped when green, and
pushed whether or not anything was fixed. These tests run the REAL script with
MAKE pointed at a small recorder that plays a scripted sequence of check results
(the Hermes call itself is exercised live by `make hermes-smoke`).

  - green on entry            -> 0 fix calls, exit 0
  - red, fixed by round 1     -> 1 fix call, stops, exit 0
  - red forever               -> FIX_ROUNDS fix calls, exit 1, report kept
  - make fix crashing         -> loop keeps going (no bash -e abort)
  - report content            -> failing check output lands in qa-report.txt
  - every check runs          -> validate, validate-search, validate-mapped, test

Run:  python3 tests/test_fix_loop.py   or   make test
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOOP = ROOT / "scripts" / "fix_loop.sh"

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


# Recorder: logs every target to calls.log. `validate` fails while the
# remaining-red counter in state/red is > 0; each `make fix` decrements it
# (FIX_EXIT controls fix's own exit code).
RECORDER = r"""#!/usr/bin/env bash
d="$(dirname "$0")"
echo "$1" >> "$d/calls.log"
red=$(cat "$d/red")
case "$1" in
  fix)
    [ "$red" -gt 0 ] && echo $((red - 1)) > "$d/red"
    exit "${FIX_EXIT:-0}" ;;
  validate)
    if [ "$red" -gt 0 ]; then echo "  FAIL: qwen3.8-27b: engine 'oMLX' has no repo url"; exit 1; fi
    echo "QA PASSED"; exit 0 ;;
  *) echo "PASSED 1 | FAILED 0"; exit 0 ;;
esac
"""


def run(red: int, rounds: int = 3, fix_exit: int = 0):
    td = Path(tempfile.mkdtemp())
    rec = td / "make"
    rec.write_text(RECORDER)
    rec.chmod(0o755)
    (td / "red").write_text(str(red))
    (td / "calls.log").write_text("")
    env = dict(os.environ, MAKE=str(rec), FIX_ROUNDS=str(rounds),
               QA_REPORT=str(td / "qa-report.txt"), FIX_EXIT=str(fix_exit))
    p = subprocess.run(["bash", str(LOOP)], env=env, capture_output=True, text=True, timeout=60)
    calls = (td / "calls.log").read_text().split()
    report = (td / "qa-report.txt").read_text() if (td / "qa-report.txt").exists() else ""
    shutil.rmtree(td)
    return p.returncode, calls, report, p.stdout


def test_green_on_entry():
    rc, calls, _, _ = run(red=0)
    check("green: exit 0", rc == 0, rc)
    check("green: no hermes fix call", "fix" not in calls, calls)
    check("green: all 4 checks ran", calls == ["validate", "validate-search", "validate-mapped", "test"], calls)


def test_fixed_in_round_one():
    rc, calls, _, out = run(red=1)
    check("round1: exit 0", rc == 0, out[-300:])
    check("round1: exactly one fix call", calls.count("fix") == 1, calls)
    check("round1: stops once green (2 check passes, no more fixes)", calls.count("validate") == 2, calls)


def test_red_forever_gives_up():
    rc, calls, report, out = run(red=99, rounds=3)
    check("red: exit 1", rc == 1, rc)
    check("red: capped at FIX_ROUNDS fix calls", calls.count("fix") == 3, calls)
    check("red: final re-check after the last fix", calls.count("validate") == 4, calls)
    check("red: report holds the real failure line", "engine 'oMLX' has no repo url" in report, report[:200])
    check("red: report marks which check failed", "=== make validate: FAILED ===" in report, report[:300])
    check("red: summary printed for the log", "manual review" in out, out[-300:])


def test_fix_crash_does_not_abort_loop():
    rc, calls, _, _ = run(red=1, fix_exit=2)
    check("crash: a non-zero make fix does not abort the loop", rc == 0 and calls.count("validate") == 2, calls)


def test_round_cap_respected():
    rc, calls, _, _ = run(red=99, rounds=1)
    check("cap: FIX_ROUNDS=1 -> one fix call", calls.count("fix") == 1 and rc == 1, calls)


def main() -> int:
    if not shutil.which("bash"):
        print("SKIP: bash not available")
        return 0
    print("fix_loop.sh control flow")
    test_green_on_entry()
    test_fixed_in_round_one()
    test_red_forever_gives_up()
    test_fix_crash_does_not_abort_loop()
    test_round_cap_respected()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
