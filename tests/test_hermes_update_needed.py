#!/usr/bin/env python3
"""Test the Hermes weekly-update decision for REAL, for every day of the week.

The CI build stage calls `make update-hermes` after building the image; its
internal if-logic (scripts/hermes_update_needed.sh) decides whether Hermes in
the container is actually updated. This test exercises that real command for
every day Mon..Sun by setting the INTERNAL CLOCK with libfaketime (so `date
+%u` returns the intended day) — no logic mocks, no fake date arguments.

For each day we run the real `make update-hermes` under faketime and assert
the branch taken: Mon..Sat -> skip, Sunday -> update. UPDATE_HERMES=1 forces
an update on any day.

Run:  python3 tests/test_hermes_update_needed.py   or   make test
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

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


# A week of dates: 2026-09-21 (Mon) .. 2026-09-27 (Sun). DOW via `date +%u`.
WEEK = {
    1: "2026-09-21",  # Mon
    2: "2026-09-22",  # Tue
    3: "2026-09-23",  # Wed
    4: "2026-09-24",  # Thu
    5: "2026-09-25",  # Fri
    6: "2026-09-26",  # Sat
    7: "2026-09-27",  # Sun
}


def run_update_hermes(date_str: str, force: bool = False) -> subprocess.CompletedProcess:
    """Run the real `make _update-hermes` recipe (the if-logic that decides
    whether Hermes is updated) with the internal clock set to date_str via
    libfaketime. Uses the host recipe directly — the public `update-hermes`
    target is just a docker wrapper around it, and this test runs inside the
    container (via make test), so nesting docker would fail."""
    env = {**os.environ, "UPDATE_HERMES": "1" if force else "0"}
    # faketime sets the clock for the whole make invocation (and its children).
    cmd = ["faketime", date_str, "make", "_update-hermes"]
    return subprocess.run(cmd, cwd=str(ROOT), env=env, capture_output=True, text=True)


def test_monday_through_saturday_skip():
    """Mon..Sat -> the real make update-hermes must SKIP (no update)."""
    for dow in (1, 2, 3, 4, 5, 6):
        r = run_update_hermes(WEEK[dow], force=False)
        out = r.stdout + r.stderr
        ok = r.returncode == 0 and "no hermes update needed" in out and "weekly hermes update" not in out
        check(f"DOW={dow} ({WEEK[dow]}) -> skip", ok, out[-200:])


def test_sunday_updates():
    """Sunday -> the real make update-hermes must run the update."""
    r = run_update_hermes(WEEK[7], force=False)
    out = r.stdout + r.stderr
    ok = r.returncode == 0 and "weekly hermes update" in out
    check("DOW=7 (2026-09-27) -> update", ok, out[-200:])


def test_force_updates_any_day():
    """UPDATE_HERMES=1 forces the update even on a non-Sunday."""
    for dow in (2, 7):
        r = run_update_hermes(WEEK[dow], force=True)
        out = r.stdout + r.stderr
        ok = r.returncode == 0 and "weekly hermes update" in out
        check(f"UPDATE_HERMES=1 DOW={dow} -> update", ok, out[-200:])


def main() -> int:
    print("hermes weekly-update decision — real make update-hermes, clock set via faketime")
    test_monday_through_saturday_skip()
    test_sunday_updates()
    test_force_updates_any_day()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
