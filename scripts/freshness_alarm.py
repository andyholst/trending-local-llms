#!/usr/bin/env python3
"""An alarm over the ARTIFACT, not over the run (issue #452).

`refresh-bot` is scheduled weekly (Wednesday `06:00` and a `17:43` same-day backup) precisely because GitHub
delays or drops on-the-hour crons. On 2026-10-20 the **06:00 run never started at all** and nothing
said so: `queued-alarm` reads runs that EXIST (a run GitHub never created has no row to read), the
sweep alarms read a delivery that exists, and `bot-health` (issue #488) reads the runs a pipeline
DID produce. Every alarm watched a run that started and went wrong.

The blast radius is the product: with the backup at 17:43 a dropped `06:00` leaves the index up to a week
stale (one lost weekly slot), and the whole fleet reports green while the visible artifact ages.

So this reads the ARTIFACT — the newest committed snapshot's own timestamp — and fails when it is
older than `MAX_AGE_HOURS`, naming the age, the newest run the pipeline did produce (if any) and
what to do. Read-only: it never comments, never dispatches.

Usage:
    python3 scripts/freshness_alarm.py [--root .] [--repo OWNER/NAME] [--max-age-hours 14] [--list]

Exit: 0 = the newest snapshot is inside the window; 1 = stale (the age and the last run are named);
2 = there is no snapshot to measure, or the age cannot be read (refusing to pass on a blind read).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SNAPSHOTS = Path("data") / "snapshots"
#: `trending-<YYYYMMDD>-<HHMMSS>.json` — the name IS the timestamp the merge wrote it at.
_NAME = re.compile(r"^trending-(\d{8})-(\d{6})\.json$")
CLOCK_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
#: Weekly (Wednesday), so the longest legitimate gap is ~7 days plus one run; 170 h (a
#: week + a day) leaves room for a slow Wednesday without ever passing a whole missed slot.
DEFAULT_MAX_AGE_HOURS = 170


def newest_snapshot(root: Path) -> tuple[datetime, Path] | None:
    """The newest snapshot in `root`, by the timestamp IN ITS NAME (never mtime: a checkout's mtime
    is the clone time, which would make every run look fresh)."""
    best: tuple[datetime, Path] | None = None
    for path in (root / SNAPSHOTS).glob("trending-*.json"):
        m = _NAME.match(path.name)
        if not m:
            continue
        try:
            when = datetime.strptime(f"{m.group(1)}{m.group(2)}", "%Y%m%d%H%M%S")
        except ValueError:
            continue
        when = when.replace(tzinfo=timezone.utc)
        if best is None or when > best[0]:
            best = (when, path)
    return best


def age_hours(when: datetime, now: datetime) -> float:
    return (now - when).total_seconds() / 3600.0


def last_refresh_run(repo: str) -> str:
    """The newest SCHEDULED refresh-bot run, as a one-line description — "none" when there is none.

    This is what distinguishes "the cron never started" (the #452 case) from "it ran and produced
    nothing", and it is reported whatever the verdict.
    """
    proc = subprocess.run(
        ["gh", "run", "list", "--repo", repo, "--workflow", "refresh-bot.yml", "--event", "schedule",
         "--limit", "1", "--json", "conclusion,createdAt,url,databaseId"],
        capture_output=True, text=True)
    if proc.returncode != 0:
        return "unknown (gh run list failed)"
    try:
        runs = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return "unknown (gh returned non-JSON)"
    if not runs:
        return "none — no scheduled refresh-bot run exists"
    r = runs[0]
    return f"{r.get('createdAt')} {r.get('conclusion')} {r.get('url')}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fail when the newest refresh snapshot is too old "
                                            "(issue #452)")
    ap.add_argument("--root", default=".")
    ap.add_argument("--repo", default="", help="OWNER/NAME, for the last-run line (default: none read)")
    ap.add_argument("--max-age-hours", type=float, default=DEFAULT_MAX_AGE_HOURS)
    ap.add_argument("--now", default="", help="an injected ISO8601Z clock (tests; issue #88)")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    found = newest_snapshot(root)
    if found is None:
        print(f"[freshness] FAIL: no data/snapshots/trending-*.json under {root} — there is "
              f"nothing to measure, which is never a pass", file=sys.stderr)
        return 2
    when, path = found
    now = (datetime.strptime(args.now, CLOCK_FORMAT).replace(tzinfo=timezone.utc)
           if args.now else datetime.now(timezone.utc))
    age = age_hours(when, now)
    run = last_refresh_run(args.repo) if args.repo else "not read (no --repo)"
    print(f"[freshness] newest snapshot: {path.name} ({when.strftime(CLOCK_FORMAT)}, "
          f"{age:.1f}h old)")
    print(f"[freshness] newest scheduled refresh-bot run: {run}")
    if age > args.max_age_hours:
        print(f"[freshness] FAIL: the newest refresh is {age:.1f}h old, over the "
              f"{args.max_age_hours:g}h window — the index a reader sees is stale. A refresh runs "
              f"weekly (Wednesday 06:00 + a 17:43 backup), so this means a week was missed or produced "
              f"nothing: check the last run line above, then dispatch refresh-bot.", file=sys.stderr)
        return 1
    print(f"[freshness] OK: the newest refresh is inside the {args.max_age_hours:g}h window")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
