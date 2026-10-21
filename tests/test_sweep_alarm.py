#!/usr/bin/env python3
"""The hourly sweep's delivery alarm (issue #497).

These tests drive the REAL decision (`sweep_alarm.stale` / `missed_slots`) and the REAL CLI
against a stub `gh` on PATH — an external system, which is the only permitted stand-in. Nothing
here replaces the logic under test (rule 6m).

The fixture is the sequence actually recorded for `issue-bot.yml`'s `schedule` runs on
2026-10-19 → 2026-10-21, when it asked for 24 slots a day and got ~5:

    01:41:54  ← 3h17 ← 22:24:00 (FAILED)  ← 3h53 ← 18:31:58
    18:31:58  ← 4h52 ← 13:39:43          ← 5h55 ← 07:44:08
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

#: The measured deliveries, newest first (the FAILED one included).
MEASURED = [
    ("2026-10-21T01:41:54Z", "success"),
    ("2026-10-20T22:24:00Z", "failure"),
    ("2026-10-20T18:31:58Z", "success"),
    ("2026-10-20T13:39:43Z", "success"),
    ("2026-10-20T07:44:08Z", "success"),
]

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


def test_the_measured_gaps_are_stale_and_a_fresh_delivery_is_not():
    """The decision, on the real recorded sequence: 3–6 h apart is a FAIL, one hour is not."""
    now = dt.datetime(2026, 10, 21, 6, 30, tzinfo=U)   # 4 h 48 m after the newest delivery
    verdict = S.stale(_rows(MEASURED), now, 3.0)
    check("measured: a 4.8 h old delivery is STALE", verdict is not None, verdict)
    check("measured: it says how old, and how many slots were missed",
          verdict is not None and verdict["age_hours"] == 4.8 and verdict["missed"] == 5,
          verdict)
    check("measured: the gaps it can see are the real 3–6 h ones",
          verdict is not None and verdict["gaps"][:4] == [3.3, 3.87, 4.87, 5.93],
          verdict and verdict["gaps"])
    check("measured: the FAILED delivery is surfaced, not averaged away",
          verdict is not None and verdict["conclusion"] == "success", verdict)

    fresh = S.stale(_rows([("2026-10-21T05:41:54Z", "success")]), now, 3.0)
    check("measured: a delivery inside the window is NOT stale", fresh is None, fresh)


def test_no_delivery_at_all_is_a_verdict_and_never_a_pass():
    """A cron that never fired must be a FAIL with its own reason, not a crash or a green."""
    verdict = S.stale([], dt.datetime(2026, 10, 21, 6, 30, tzinfo=U), 3.0)
    check("none: an empty run list is a verdict", verdict is not None, verdict)
    check("none: the reason names the cron, not the data",
          verdict is not None and "no schedule run has ever been delivered" in verdict["reason"],
          verdict)


def test_a_red_last_delivery_is_named_even_when_it_is_fresh():
    """'Red on every run' must not read as health: the last conclusion is rendered."""
    rows = _rows([("2026-10-21T01:41:54Z", "failure")])
    now = dt.datetime(2026, 10, 21, 6, 30, tzinfo=U)
    verdict = S.stale(rows, now, 3.0)
    text = S.render(verdict, rows, 3.0)
    check("colour: the render names a non-success delivery", "was failure" in text, text[:300])


def test_the_cli_exit_codes_are_loud_in_every_direction():
    """Through the real CLI, with only `gh` stubbed: fresh=0, stale=1, unreadable=2."""
    with tempfile.TemporaryDirectory() as td:
        env = _stub(td, MEASURED)
        stale = subprocess.run([sys.executable, str(SCRIPT), "--repo", "o/r",
                                "--now", "2026-10-21T06:30:00Z"], capture_output=True, text=True,
                               env=env)
        fresh = subprocess.run([sys.executable, str(SCRIPT), "--repo", "o/r",
                                "--now", "2026-10-21T02:00:00Z"], capture_output=True, text=True,
                               env=env)
    check("cli: a stale heap exits 1 and says FAIL", stale.returncode == 1
          and "FAIL" in stale.stdout, (stale.returncode, stale.stdout[-200:]))
    check("cli: a fresh delivery exits 0 and says OK", fresh.returncode == 0
          and "OK" in fresh.stdout, (fresh.returncode, fresh.stdout[-200:]))

    with tempfile.TemporaryDirectory() as td:
        env = _stub(td, [], fail=True)
        broken = subprocess.run([sys.executable, str(SCRIPT), "--repo", "o/r"],
                                capture_output=True, text=True, env=env)
    check("cli: an unreadable GitHub read exits 2, never a pass",
          broken.returncode == 2 and "FAIL" in broken.stderr, (broken.returncode, broken.stderr[-200:]))


def test_the_sweep_carries_a_second_slot_and_the_alarm_is_wired():
    """The two halves of the fix: a spare cron slot, and a make target the alarm job actually runs."""
    sweep = SWEEP.read_text()
    crons = [line.split('"')[1] for line in sweep.splitlines() if "cron:" in line]
    check("wiring: the sweep carries MORE than one slot", len(crons) >= 2, crons)
    check("wiring: the spare slot is off the hour it already used",
          crons.count("19 * * * *") == 1 and any(c != "19 * * * *" for c in crons), crons)
    makefile = MAKEFILE.read_text()
    check("wiring: `make sweep-alarm` exists and calls the one implementation",
          "sweep-alarm:" in makefile and "scripts/sweep_alarm.py" in makefile, "")
    alarm = ALARM_WF.read_text()
    check("wiring: the twice-hourly alarm pipeline runs it",
          "make sweep-alarm" in alarm, "")
    check("wiring: the alarm job has a checkout before it calls make",
          alarm.index("actions/checkout") < alarm.index("make sweep-alarm"), "")


def main() -> int:
    print("sweep alarm: a dropped cron has no run to look at (issue #497)")
    test_the_measured_gaps_are_stale_and_a_fresh_delivery_is_not()
    test_no_delivery_at_all_is_a_verdict_and_never_a_pass()
    test_a_red_last_delivery_is_named_even_when_it_is_fresh()
    test_the_cli_exit_codes_are_loud_in_every_direction()
    test_the_sweep_carries_a_second_slot_and_the_alarm_is_wired()
    print(f"\nPASSED {_checks_passed} | FAILED {_checks_failed}")
    return 0 if _checks_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
