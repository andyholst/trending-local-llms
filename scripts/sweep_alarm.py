#!/usr/bin/env python3
"""Fail loudly when the hourly sweep has not been DELIVERED (issue #497).

`issue-bot.yml` asks GitHub for `cron: "19 * * * *"` and takes ONE issue per delivery. GitHub
drops and delays scheduled runs: the recorded sequence for 2026-10-19 → 2026-10-21 was

    01:41:54  ← 3h17 ← 22:24:00 (FAILED)  ← 3h53 ← 18:31:58
    18:31:58  ← 4h52 ← 13:39:43          ← 5h55 ← 07:44:08

— ~5 deliveries a day out of 24 slots. `queued-alarm` cannot see this: it reads runs that EXIST
(`queued` / `in_progress`), and a slot GitHub never created has no run to look at. This tool
reads the ARTIFACT instead — the newest `schedule` run of the sweep:

  * age of the newest delivery, against `--max-age-hours` (default 3),
  * how many slots it should have had by now, and the gaps between the runs it can see,
  * the last run's conclusion, so a sweep that is red on every delivery is visible too.

Exit codes: 0 = the newest delivery is fresh, 1 = it is stale (or none was ever delivered), so
the twice-hourly alarm job goes RED instead of staying quiet, 2 = the GitHub read failed (a
tool that cannot read must not report a pass).

Read-only: this tool never comments, never dispatches and never touches a run.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys

WORKFLOW = "issue-bot.yml"
#: The sweep runs at :19 past every hour. Kept here as the schedule the alarm measures against,
#: so "3 hours stale" means "3 slots were missed", not "3 × some interval".
SLOT_MINUTE = 19


def _gh(args: list[str]) -> str:
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {out.stderr.strip()}")
    return out.stdout


def _ts(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def deliveries(repo: str, limit: int = 20) -> list[dict]:
    """The workflow's `schedule` runs, newest first, as `{id, at, conclusion, url}`.

    Only `schedule` runs: a `workflow_dispatch` or an `issues:`-event run proves the pipeline can
    start, not that the CRON was delivered — and this alarm exists for the cron.
    """
    raw = _gh(["run", "list", "--workflow", WORKFLOW, "--event", "schedule", "--limit", str(limit),
               "--json", "databaseId,createdAt,conclusion,status,url", "--repo", repo])
    rows = []
    for r in json.loads(raw or "[]"):
        at = _ts(r.get("createdAt"))
        if at is None:
            continue
        rows.append({"id": r.get("databaseId"), "at": at,
                     "conclusion": r.get("conclusion") or r.get("status") or "unknown",
                     "url": r.get("url") or ""})
    return sorted(rows, key=lambda r: r["at"], reverse=True)


def missed_slots(newest: dt.datetime, now: dt.datetime) -> int:
    """How many `:19` slots should have produced a run since `newest` (exclusive)."""
    if newest >= now:
        return 0
    count, cursor = 0, newest
    while True:
        nxt = (cursor + dt.timedelta(hours=1)).replace(minute=SLOT_MINUTE, second=0, microsecond=0)
        if nxt > now:
            break
        count += 1
        cursor = nxt
    return count


def stale(rows: list[dict], now: dt.datetime, max_age_hours: float) -> dict | None:
    """The verdict as data — None when the newest delivery is fresh.

    Pure (rule 6d): the decision is testable without a network, and "no run at all" is a verdict
    of its own rather than a crash.
    """
    if not rows:
        return {"reason": "no schedule run has ever been delivered", "age_hours": None,
                "newest": None, "conclusion": None, "missed": None, "gaps": []}
    newest = rows[0]
    age = (now - newest["at"]).total_seconds() / 3600.0
    gaps = [round((a["at"] - b["at"]).total_seconds() / 3600.0, 2)
            for a, b in zip(rows, rows[1:])]
    if age <= max_age_hours:
        # A delivery that RAN and did not succeed is not a delivery (issue #498). The
        # alarm proved the cron, not the work: a sweep that dies inside `implement`, or
        # is cancelled by `concurrency: issue-bot-issue-<n>`, is FRESH to an age test and
        # read as healthy — measured on runs 40190558547 and 40194644167, where `pick`
        # failed at 11:50 and 12:46 and this alarm reported OK both times.
        if newest.get("conclusion") == "success":
            return None
        return {"reason": (f"the newest delivery is only {age:.1f} h old but concluded "
                           f"'{newest.get('conclusion')}' — a sweep that ran and did not "
                           f"succeed delivered nothing"),
                "age_hours": round(age, 2), "newest": newest["at"],
                "conclusion": newest.get("conclusion"), "missed": 0, "gaps": gaps[:6],
                "url": newest.get("url"), "fresh": True}
    return {"reason": f"the newest delivery is {age:.1f} h old (max {max_age_hours} h)",
            "age_hours": round(age, 2), "newest": newest["at"], "conclusion": newest["conclusion"],
            "missed": missed_slots(newest["at"], now), "gaps": gaps[:6], "url": newest["url"]}


def render(verdict: dict, rows: list[dict], max_age_hours: float) -> str:
    lines = [f"[sweep-alarm] FAIL: {verdict['reason']}"]
    if verdict.get("newest") is None:
        lines.append(f"  {WORKFLOW} has no `schedule` run at all — the cron never fired, or the "
                     f"workflow is disabled")
        return "\n".join(lines)
    lines += [
        f"  newest schedule run: {verdict['newest'].strftime('%Y-%m-%dT%H:%M:%SZ')} "
        f"({verdict['conclusion']})",
        f"  slots missed since then: {verdict['missed']} (the sweep asks for one at :{SLOT_MINUTE:02d} "
        f"every hour)",
    ]
    if verdict.get("gaps"):
        lines.append("  gaps between the deliveries it can see: "
                     + ", ".join(f"{g} h" for g in verdict["gaps"]))
    if verdict["conclusion"] not in ("success", None):
        lines.append(f"  the LAST delivery was {verdict['conclusion']} — a sweep that is red on "
                     f"every run looks the same as a missing one from here")
    if verdict.get("fresh"):
        lines.append("  the delivery is FRESH: this is not a dropped cron, it is a sweep that "
                     "ran and did not succeed (issue #498) — the queue did not drain")
    lines += [
        f"  the hourly queue is not being drained at one issue per hour; MAX_AGE_HOURS="
        f"{max_age_hours}",
        "  a dropped cron has no run to look at — that is why this reads the ARTIFACT (issue #497)",
    ]
    if verdict.get("url"):
        lines.append(f"  last run: {verdict['url']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Fail loudly when the hourly sweep has not been DELIVERED (issue #497)")
    ap.add_argument("--repo", required=True, help="owner/name")
    ap.add_argument("--max-age-hours", type=float, default=3.0,
                    help="how stale the newest delivery may be (default 3)")
    ap.add_argument("--now", default=None, help="Iso8601 instant to measure from (tests)")
    ap.add_argument("--limit", type=int, default=20, help="how many deliveries to read")
    args = ap.parse_args(argv)

    now = _ts(args.now) or dt.datetime.now(dt.timezone.utc)
    try:
        rows = deliveries(args.repo, args.limit)
    except (RuntimeError, ValueError) as exc:
        print(f"[sweep-alarm] FAIL: {exc}", file=sys.stderr)
        return 2

    verdict = stale(rows, now, args.max_age_hours)
    if verdict is None:
        newest = rows[0]
        print(f"[sweep-alarm] OK: newest schedule delivery "
              f"{newest['at'].strftime('%Y-%m-%dT%H:%M:%SZ')} ({newest['conclusion']}), "
              f"within {args.max_age_hours} h")
        return 0
    print(render(verdict, rows, args.max_age_hours))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
