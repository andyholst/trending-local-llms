#!/usr/bin/env python3
"""The weekly sweep's delivery alarm (issue #497).

These tests drive the REAL decision (`sweep_alarm.stale` / `missed_slots`) and the REAL CLI
against a stub `gh` on PATH — an external system, which is the only permitted stand-in. Nothing
here replaces the logic under test (rule 6m).

The sweep now asks for ONE delivery per Wednesday (`cron: "19 * * * 3"` plus a `49 * * * 3`
backup). The alarm measures the age of the newest delivery against `--max-age-hours` (default
168 = a week) and the number of Wednesday slots missed since it, so "stale" means "a whole
weekly slot was missed", not "3 × some hourly interval". The measured failures that earned this
alarm (dropped crons on 2026-10-19 → 10-21) are preserved as history, not as the live cadence.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import sweep_alarm as S  # noqa: E402  (the module under test, imported for its pure decision)

SCRIPT = ROOT / "scripts" / "sweep_alarm.py"
MAKEFILE = ROOT / "Makefile"
SWEEP = ROOT / ".github" / "workflows" / "issue-bot.yml"
ALARM_WF = ROOT / ".github" / "workflows" / "queued-alarm.yml"
U = dt.timezone.utc

#: Weekly deliveries, newest first — each on a Wednesday (the FAILED one included).
MEASURED = [
    ("2026-10-21T01:41:54Z", "success"),
    ("2026-10-14T02:00:00Z", "failure"),
    ("2026-10-07T01:30:00Z", "success"),
    ("2026-09-30T02:00:00Z", "success"),
]
#: The Wednesday after the newest delivery: 8 days on, at :19 → it should have run again.
_NOW_STALE = dt.datetime(2026, 10, 28, 6, 30, tzinfo=U)

_checks_passed = 0
_checks_failed = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global _checks_passed, _checks_failed
    if ok:
        _checks_passed += 1
        print(f"  ok  {name}")
    else:
        _checks_failed += 1
        print(f"  FAIL {name}  [{detail}]")


def _rows(pairs: list[tuple[str, str]]) -> list[dict]:
    return [{"id": i, "at": S._ts(ts), "conclusion": c, "url": f"https://x/run/{i}"}
            for i, (ts, c) in enumerate(pairs)]


def _stub(td: str, runs: list[tuple[str, str]], *, fail: bool = False) -> dict:
    """A `gh` on PATH that answers `run list` with `runs` — the network, nothing else."""
    gh = Path(td) / "gh"
    payload = Path(td) / "runs.json"
    payload.write_text(json.dumps([
        {"databaseId": i, "createdAt": ts, "conclusion": c, "status": "completed",
         "url": f"https://x/run/{i}"} for i, (ts, c) in enumerate(runs)]))
    gh.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        + ("echo 'HTTP 403: Resource not accessible' >&2\nexit 1\n" if fail else
           f'cat "{payload}"\n'))
    gh.chmod(0o755)
    return {**os.environ, "PATH": f"{td}:{os.environ['PATH']}"}


def test_a_missed_weekly_slot_is_stale_and_a_fresh_delivery_is_not():
    """The decision, on the real recorded sequence set weekly: a missed Wednesday is a FAIL."""
    # 8 days after the newest delivery (its only successor should have been a Wednesday ago).
    now = _NOW_STALE
    verdict = S.stale(_rows(MEASURED), now, 168.0)
    check("weekly: an 8-day-old delivery is STALE", verdict is not None, verdict)
    check("weekly: it says how old, and how many Wednesday slots were missed",
          verdict is not None and verdict["missed"] == 1, verdict)
    check("weekly: the FAILED delivery is surfaced, not averaged away",
          verdict is not None and verdict["conclusion"] == "success", verdict)

    # A delivery within the weekly window (a few hours ago, same Wednesday) is fresh.
    fresh = S.stale(_rows([("2026-10-21T05:41:54Z", "success")]),
                    dt.datetime(2026, 10, 21, 6, 30, tzinfo=U), 168.0)
    check("weekly: a same-day delivery is NOT stale", fresh is None, fresh)


def test_no_delivery_at_all_is_a_verdict_and_never_a_pass():
    """A cron that never fired must be a FAIL with its own reason, not a crash or a green."""
    verdict = S.stale([], _NOW_STALE, 168.0)
    check("none: an empty run list is a verdict", verdict is not None, verdict)
    check("none: the reason names the cron, not the data",
          verdict is not None and "no schedule run has ever been delivered" in verdict["reason"],
          verdict)


def test_a_red_last_delivery_is_loud_even_when_it_is_FRESH():
    """Issue #498: a sweep that ran and failed is a VERDICT, not a fresh delivery.

    The measured failure is exactly the opposite: `pick` died and the alarm said OK because
    the run existed and was recent. Freshness never excuses a red conclusion.
    """
    rows = _rows([("2026-10-21T06:00:00Z", "failure")])          # 30 minutes old
    now = dt.datetime(2026, 10, 21, 6, 30, tzinfo=U)
    verdict = S.stale(rows, now, 168.0)

    check("fresh-red: a fresh FAILED delivery is a verdict", verdict is not None, verdict)
    check("fresh-red: the verdict is marked fresh, so it is not read as a dropped cron",
          verdict is not None and verdict.get("fresh") is True, verdict)
    check("fresh-red: the reason names the conclusion",
          verdict is not None and "failure" in verdict["reason"], verdict)
    text = S.render(verdict, rows, 168.0)
    check("fresh-red: the render says FRESH and that the queue did not drain",
          "FRESH" in text and "did not drain" in text, text[:400])
    check("fresh-red: it still names the run", "run/0" in text, text[:400])

    ok = S.stale(_rows([("2026-10-21T06:00:00Z", "success")]), now, 168.0)
    check("fresh-red: a fresh successful delivery is still OK", ok is None, ok)

    cancelled = S.stale(_rows([("2026-10-21T06:00:00Z", "cancelled")]), now, 168.0)
    check("fresh-red: a cancelled sweep is not health either",
          cancelled is not None and "cancelled" in cancelled["reason"], cancelled)


def test_the_cli_exit_codes_are_loud_in_every_direction():
    """Through the real CLI, with only `gh` stubbed: fresh=0, stale=1, unreadable=2."""
    with tempfile.TemporaryDirectory() as td:
        env = _stub(td, MEASURED)
        stale = subprocess.run([sys.executable, str(SCRIPT), "--repo", "o/r",
                                "--now", "2026-10-28T06:30:00Z"], capture_output=True, text=True,
                               env=env)
        fresh = subprocess.run([sys.executable, str(SCRIPT), "--repo", "o/r",
                                "--now", "2026-10-21T02:00:00Z"], capture_output=True, text=True,
                               env=env)
    check("cli: a stale heap exits 1 and says FAIL", stale.returncode == 1
          and "FAIL" in stale.stdout, (stale.returncode, stale.stdout[-200:]))
    check("cli: a fresh delivery exits 0 and says OK", fresh.returncode == 0
          and "OK" in fresh.stdout, (fresh.returncode, fresh.stdout[-200:]))

    with tempfile.TemporaryDirectory() as td:
        env = _stub(td, [("2026-10-21T01:41:54Z", "failure")])
        fresh_red = subprocess.run([sys.executable, str(SCRIPT), "--repo", "o/r",
                                    "--now", "2026-10-21T02:00:00Z"],
                                   capture_output=True, text=True, env=env)
    check("cli: a fresh FAILED delivery exits 1 and says FRESH",
          fresh_red.returncode == 1 and "FRESH" in fresh_red.stdout,
          (fresh_red.returncode, fresh_red.stdout[-300:]))

    with tempfile.TemporaryDirectory() as td:
        env = _stub(td, [], fail=True)
        broken = subprocess.run([sys.executable, str(SCRIPT), "--repo", "o/r"],
                                capture_output=True, text=True, env=env)
    check("cli: an unreadable GitHub read exits 2, never a pass",
          broken.returncode == 2 and "FAIL" in broken.stderr, (broken.returncode, broken.stderr[-200:]))


def test_the_sweep_carries_a_second_slot_and_the_alarm_is_wired():
    """The two halves of the fix: a spare (Wednesday) cron slot, and a make target the alarm runs."""
    sweep = SWEEP.read_text()
    crons = [line.split('"')[1] for line in sweep.splitlines() if "cron:" in line]
    check("wiring: the sweep carries MORE than one slot", len(crons) >= 2, crons)
    check("wiring: both slots are on Wednesday and off the hour",
          "19 * * * 3" in crons and "49 * * * 3" in crons, crons)
    makefile = MAKEFILE.read_text()
    check("wiring: `make sweep-alarm` exists and calls the one implementation",
          "sweep-alarm:" in makefile and "scripts/sweep_alarm.py" in makefile, "")
    alarm = ALARM_WF.read_text()
    check("wiring: the weekly alarm pipeline runs it", "make sweep-alarm" in alarm, "")
    check("wiring: the alarm job has a checkout before it calls make",
          alarm.index("actions/checkout") < alarm.index("make sweep-alarm"), "")


def main() -> int:
    print("sweep alarm: a dropped cron has no run to look at (issue #497)")
    test_a_missed_weekly_slot_is_stale_and_a_fresh_delivery_is_not()
    test_no_delivery_at_all_is_a_verdict_and_never_a_pass()
    test_a_red_last_delivery_is_loud_even_when_it_is_FRESH()
    test_the_cli_exit_codes_are_loud_in_every_direction()
    test_the_sweep_carries_a_second_slot_and_the_alarm_is_wired()
    print(f"\nPASSED {_checks_passed} | FAILED {_checks_failed}")
    return 0 if _checks_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
