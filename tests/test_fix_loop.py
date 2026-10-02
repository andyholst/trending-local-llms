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
  - reasoning budget burnt    -> same round retried once with HERMES_FIX_REASONING=none
                                 (PR #80: 2 of 3 rounds wrote nothing at 'low')
  - report = failing check only -> passing checks' unit-suite noise stays out

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
echo "$*" | tr ' ' '+' >> "$d/calls.log"
red=$(cat "$d/red")
case "$1" in
  fix)
    if [ "${BUDGET_BURN:-0}" = "1" ] && [ "$2" != "HERMES_FIX_REASONING=none" ]; then
      echo "No visible answer was produced. The model hit its output-token limit on every continuation attempt - its reasoning consumed the entire budget each time."
      exit 2
    fi
    [ "$red" -gt 0 ] && echo $((red - 1)) > "$d/red"
    exit "${FIX_EXIT:-0}" ;;
  validate-search)
    echo "  ok  mapping: id match"
    echo "  FAIL: m1: duplicate model ids in models.json: ['m1']"
    if [ "${VS_RED:-0}" = "1" ]; then echo "  FAIL mapping: real regression"; echo "PASSED 4 | FAILED 1"; exit 1; fi
    echo "PASSED 5 | FAILED 0"; exit 0 ;;
  validate)
    if [ "$red" -gt 0 ]; then echo "  FAIL: qwen3.8-27b: engine 'oMLX' has no repo url"; exit 1; fi
    echo "QA PASSED"; exit 0 ;;
  test)
    # negative tests print validator FAIL lines from their fixtures - noise
    echo "  FAIL: m1: duplicate model ids in models.json: ['m1']"
    if [ "${TEST_RED:-0}" = "1" ]; then echo "  FAIL readme-render: trend cell"; echo "PASSED 9 | FAILED 1"; exit 1; fi
    echo "PASSED 10 | FAILED 0"; exit 0 ;;
  *) echo "PASSED 1 | FAILED 0"; exit 0 ;;
esac
"""


def run(red: int, rounds: int = 3, fix_exit: int = 0, test_red: int = 0, budget_burn: int = 0, vs_red: int = 0):
    td = Path(tempfile.mkdtemp())
    rec = td / "make"
    rec.write_text(RECORDER)
    rec.chmod(0o755)
    (td / "red").write_text(str(red))
    (td / "calls.log").write_text("")
    env = dict(os.environ, MAKE=str(rec), FIX_ROUNDS=str(rounds),
               QA_REPORT=str(td / "qa-report.txt"), FIX_EXIT=str(fix_exit), TEST_RED=str(test_red),
               BUDGET_BURN=str(budget_burn), VS_RED=str(vs_red))
    p = subprocess.run(["bash", str(LOOP)], env=env, capture_output=True, text=True, timeout=60)
    calls = [c.split("+")[0] for c in (td / "calls.log").read_text().split()]
    raw_calls = (td / "calls.log").read_text().split()
    report = (td / "qa-report.txt").read_text() if (td / "qa-report.txt").exists() else ""
    shutil.rmtree(td)
    run.raw_calls = raw_calls
    return p.returncode, calls, report, p.stdout


def test_green_on_entry():
    rc, calls, _, _ = run(red=0)
    check("green: exit 0", rc == 0, rc)
    check("green: no hermes fix call", "fix" not in calls, calls)
    check("green: checks fast -> slow, unit suite last",
          calls == ["validate-search", "validate-mapped", "validate", "test"], calls)


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


def test_stops_at_first_red_and_skips_unit_suite():
    rc, calls, report, out = run(red=99, rounds=1)
    check("speed: 'make test' never runs while a validate check is red", "test" not in calls, calls)
    check("speed: nothing after the first red check in a round",
          calls[:3] == ["validate-search", "validate-mapped", "validate"] and calls[3] == "fix", calls)


def test_unit_suite_failure_is_red():
    rc, calls, report, out = run(red=0, rounds=1, test_red=1)
    check("suite: validates green but a unit test red -> loop is red", rc == 1, out[-200:])
    check("suite: the unit-test failure reaches the summary", "FAIL readme-render: trend cell" in out, out[-300:])


def test_summary_drops_fixture_noise():
    rc, calls, report, out = run(red=0, rounds=1, test_red=1)
    summary = out.split("still RED", 1)[-1]
    check("summary: negative-test fixture lines ('FAIL: m1 ...') are not reported",
          "FAIL: m1" not in summary, summary[-300:])
    check("summary: the failing suite total is reported", "PASSED 9 | FAILED 1" in summary, summary[-300:])
    rc, calls, report, out = run(red=99, rounds=1)
    check("summary: real validator failures are reported",
          "engine 'oMLX' has no repo url" in out.split("still RED", 1)[-1], out[-300:])


def test_budget_burn_retries_with_reasoning_off():
    rc, calls, _, out = run(red=1, rounds=3, budget_burn=1)
    raw = run.raw_calls
    check("budget: retried in the same round with HERMES_FIX_REASONING=none",
          "fix+HERMES_FIX_REASONING=none" in raw, raw)
    check("budget: the retry fixes it in round 1 (one round, then green)",
          rc == 0 and calls.count("validate") == 2, raw)
    check("budget: the retry is announced in the log", "retrying this round with HERMES_FIX_REASONING=none" in out,
          out[-300:])
    rc, calls, _, out = run(red=1, rounds=3, fix_exit=2)
    check("budget: an ordinary make-fix failure is NOT retried with reasoning off",
          not any("HERMES_FIX_REASONING=none" in c for c in run.raw_calls), run.raw_calls)


def test_report_holds_only_the_failing_check():
    rc, calls, report, out = run(red=99, rounds=1)
    check("report: names the checks that passed", "checks passed: validate-search validate-mapped" in report,
          report[:200])
    check("report: no output from passing checks (their fixture noise)", "FAIL: m1" not in report, report[:300])
    rc, calls, report, out = run(red=0, rounds=1, vs_red=1)
    summary = out.split("still RED", 1)[-1]
    check("summary: a unit-suite failure inside validate-search is reported",
          "FAIL mapping: real regression" in summary, summary[-300:])
    check("summary: fixture lines inside validate-search are dropped", "FAIL: m1" not in summary, summary[-300:])


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
    test_stops_at_first_red_and_skips_unit_suite()
    test_unit_suite_failure_is_red()
    test_summary_drops_fixture_noise()
    test_budget_burn_retries_with_reasoning_off()
    test_report_holds_only_the_failing_check()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
