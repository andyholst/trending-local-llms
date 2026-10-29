#!/usr/bin/env python3
"""An alarm over the ARTIFACT, not over the run (issue #452).

On 2026-10-20 the 06:00 refresh never started at all: `queued-alarm` read runs that EXIST (a run
GitHub never created has no row), `sweep-alarm` read a delivery that exists, and `bot-health` reads
the runs a pipeline did produce. The index sat stale while the whole fleet reported green.

These tests drive the REAL script against real directory trees and an injected clock (`--now`), and
read the REAL workflow — never the wall clock, which is the #88 defect.

Run:  python3 tests/test_freshness_alarm.py    or   make test
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "freshness_alarm.py"

_PASS = 0
_FAIL = 0


def check(name, cond, detail=None):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        shown = "" if detail is None or detail == "" else f"  [{detail}]"
        print(f"  FAIL {name}{shown}")


def tree(td: Path, names: list[str]) -> Path:
    (td / "data" / "snapshots").mkdir(parents=True, exist_ok=True)
    for name in names:
        (td / "data" / "snapshots" / name).write_text("{}\n")
    return td


def run(*args: str):
    import subprocess
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def test_a_fresh_snapshot_passes():
    with tempfile.TemporaryDirectory() as d:
        root = tree(Path(d), ["trending-20261025-060000.json"])
        p = run("--root", str(root), "--now", "2026-10-25T12:00:00Z")
        check("fresh: a 6 h old snapshot is inside the weekly (170 h) window", p.returncode == 0,
              (p.returncode, p.stderr[-200:]))
        check("fresh: it names the snapshot it measured", "trending-20261025-060000.json" in p.stdout,
              p.stdout)


def test_a_stale_snapshot_fails_and_names_the_age():
    with tempfile.TemporaryDirectory() as d:
        root = tree(Path(d), ["trending-20261010-060000.json"])
        p = run("--root", str(root), "--now", "2026-10-25T12:00:00Z")
        # A snapshot from 15 days earlier is well outside the weekly window (170 h).
        check("stale: a 15-day-old snapshot fails the alarm", p.returncode == 1, p.returncode)
        check("stale: it states the age and the window",
              "366.0h old" in p.stderr and "170h window" in p.stderr, p.stderr[-300:])
        check("stale: it says what a human should do",
              "dispatch refresh-bot" in p.stderr, p.stderr[-300:])


def test_the_newest_snapshot_wins_not_the_first_on_disk():
    with tempfile.TemporaryDirectory() as d:
        root = tree(Path(d), ["trending-20261025-060000.json", "trending-20261020-060000.json",
                              "trending-20261024-180000.json"])
        p = run("--root", str(root), "--now", "2026-10-25T07:00:00Z")
        check("newest: the newest NAME is measured, not the directory order",
              p.returncode == 0 and "20261025-060000" in p.stdout, (p.returncode, p.stdout))


def test_no_snapshot_at_all_is_never_a_pass():
    with tempfile.TemporaryDirectory() as d:
        root = tree(Path(d), [])
        p = run("--root", str(root), "--now", "2026-10-25T12:00:00Z")
        check("missing: no snapshot exits 2 (nothing to measure is not health)",
              p.returncode == 2, p.returncode)
        check("missing: it says so", "nothing to measure" in p.stderr, p.stderr[-200:])


def test_a_file_mtime_never_makes_a_stale_tree_fresh():
    """A clone's mtime is the CLONE time: measuring it would make every run look fresh."""
    import os
    with tempfile.TemporaryDirectory() as d:
        root = tree(Path(d), ["trending-20261003-060000.json"])
        path = root / "data" / "snapshots" / "trending-20261003-060000.json"
        os.utime(path, (2_000_000_000, 2_000_000_000))     # "modified now"
        p = run("--root", str(root), "--now", "2026-10-25T12:00:00Z")
        check("mtime: a touched stale snapshot is still stale", p.returncode == 1, p.returncode)


def test_the_workflow_runs_it_beside_the_sweep_alarm():
    wf = (ROOT / ".github" / "workflows" / "queued-alarm.yml").read_text()
    check("workflow: the freshness step exists", "make freshness-alarm" in wf, "")
    check("workflow: it runs the same job as the sweep alarm, after it",
          0 <= wf.find("make sweep-alarm") < wf.find("make freshness-alarm"), "")
    check("workflow: it uses the default token (the owner PAT cannot comment/read here)",
          "GH_TOKEN: ${{ github.token }}" in wf, "")
    makefile = (ROOT / "Makefile").read_text()
    check("makefile: the target exists", "\nfreshness-alarm:" in makefile, "")
    check("makefile: it forwards MAX_AGE_HOURS", 'MAX_AGE_HOURS)' in makefile, "")


def main() -> int:
    print("freshness alarm: the ARTIFACT, not the run (issue #452)")
    test_a_fresh_snapshot_passes()
    test_a_stale_snapshot_fails_and_names_the_age()
    test_the_newest_snapshot_wins_not_the_first_on_disk()
    test_no_snapshot_at_all_is_never_a_pass()
    test_a_file_mtime_never_makes_a_stale_tree_fresh()
    test_the_workflow_runs_it_beside_the_sweep_alarm()
    print(f"PASSED {_PASS} | FAILED {_FAIL}")
    return 0 if _FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
