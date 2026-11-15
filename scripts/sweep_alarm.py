#!/usr/bin/env python3
"""Fail loudly when the sweep's newest DELIVERED run is red or hung (issue #497; the
dispatch-only mode is issue #1029 — the owner directive of 2026-11-15 removed the sweep's
cron, so age alone never reds; only a FAILED or HUNG dispatch does).

`issue-bot.yml` used to ask GitHub for `cron: "19 * * * 3"` (Wednesdays) and take ONE issue
per delivery. GitHub
drops and delays scheduled runs: the recorded sequence for 2026-10-19 → 2026-10-21 was

    01:41:54  ← 3h17 ← 22:24:00 (FAILED)  ← 3h53 ← 18:31:58
    18:31:58  ← 4h52 ← 13:39:43          ← 5h55 ← 07:44:08

— on a daily cadence those measured ~5 deliveries a day out of 24 slots; the sweep is now weekly (Wednesday). `queued-alarm` cannot see this: it reads runs that EXIST
(`queued` / `in_progress`), and a slot GitHub never created has no run to look at. This tool
reads the ARTIFACT instead — the newest `schedule` run of the sweep:

  * age of the newest delivery, against `--max-age-hours` (default 168),
  * how many slots it should have had by now, and the gaps between the runs it can see,
  * the last run's conclusion, so a sweep that is red on every delivery is visible too.

Exit codes: 0 = the newest delivery is fresh, 1 = it is stale (or none was ever delivered), so
the alarm job goes RED instead of staying quiet, 2 = the GitHub read failed (a
tool that cannot read must not report a pass).

A delivery the run list has not CONCLUDED yet (`in_progress` / `queued`) proves nothing about
the queue (issue #801): graded mid-flight it looked like a failed sweep — measured on
`queued-alarm` #87/#88, which went red 14 minutes into the very sweep that succeeded at 19:03Z.
Such a delivery is PENDING (exit 0) until `--inflight-cap-hours` (default 3); past the cap it is
HUNG, which is loud. A CONCLUDED failure keeps the fresh-red verdict of issue #498 unchanged.

Read-only: this tool never comments, never dispatches and never touches a run.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

WORKFLOW = "issue-bot.yml"
ROOT = Path(__file__).resolve().parent.parent
#: Whether the sweep pipeline still OWES a weekly delivery (a `schedule:` block in its
#: workflow). Issue #1029 (owner directive 2026-11-15) made the sweep dispatch-only: age
#: alone is then not a failure — only a FAILED or HUNG dispatched delivery is. Derived
#: from the tree (rule 6d), never from a hand-kept flag.
def workflow_declares_schedule(workflows_dir: Path) -> bool:
    return re.search(r"^\s{2}schedule:\s*$",
                     (workflows_dir / WORKFLOW).read_text(), re.M) is not None
#: The sweep runs at :19 on Wednesdays. Kept here as the schedule the alarm measures against,
#: so "1 week stale" means "1 slot was missed", not "some interval".
SLOT_MINUTE = 19
#: Python `date.weekday()`: 0=Mon … 2=Wed. Matches the cron `* * 3`.
SLOT_WEEKDAY = 2
#: Conclusions the run list uses for a run that has not finished (issue #801). A delivery with
#: one of these has delivered NO verdict yet — it is in flight, not failed.
INFLIGHT_CONCLUSIONS = ("in_progress", "queued", "in_queue")


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

    Every event counts now (issue #1029): the sweep is dispatch-only, so a
    `workflow_dispatch` run IS the delivery this alarm measures. While a cron existed,
    only `schedule` runs proved the cron was delivered; the mode decision lives in
    `workflow_declares_schedule`, not in the run filter.
    """
    raw = _gh(["run", "list", "--workflow", WORKFLOW, "--limit", str(limit),
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
    """How many Wednesday `:19` slots should have produced a run since `newest` (exclusive)."""
    if newest >= now:
        return 0
    count, cursor = 0, newest
    while True:
        nxt = (cursor + dt.timedelta(days=7)).replace(hour=1, minute=SLOT_MINUTE, second=0, microsecond=0)
        nxt = nxt - dt.timedelta(days=(nxt.weekday() - SLOT_WEEKDAY) % 7)
        if nxt > now:
            break
        count += 1
        cursor = nxt
    return count


def stale(rows: list[dict], now: dt.datetime, max_age_hours: float,
          inflight_cap_hours: float = 3.0, scheduled: bool = True) -> dict | None:
    """The verdict as data — None when the newest delivery is fresh and green.

    Pure (rule 6d): the decision is testable without a network, and "no run at all" is a verdict
    of its own rather than a crash. `scheduled` (issue #1029): when the sweep carries no cron,
    age alone is not a failure — a dispatch-only sweep owes no weekly slot, so a green delivery
    of any age (or no delivery at all) reports OK; a FAILED or HUNG dispatch still goes red.
    """
    if not rows:
        if not scheduled:
            return None
        return {"reason": "no schedule run has ever been delivered", "age_hours": None,
                "newest": None, "conclusion": None, "missed": None, "gaps": []}
    newest = rows[0]
    age = (now - newest["at"]).total_seconds() / 3600.0
    gaps = [round((a["at"] - b["at"]).total_seconds() / 3600.0, 2)
            for a, b in zip(rows, rows[1:])]
    if age <= max_age_hours:
        conclusion = newest.get("conclusion")
        # A delivery that RAN and did not succeed is not a delivery (issue #498). The
        # alarm proved the cron, not the work: a sweep that dies inside `implement`, or
        # is cancelled by `concurrency: issue-bot-issue-<n>`, is FRESH to an age test and
        # read as healthy — measured on runs 40190558547 and 40194644167, where `pick`
        # failed at 11:50 and 12:46 and this alarm reported OK both times.
        if conclusion == "success":
            return None
        # But a delivery the run list has NOT CONCLUDED yet is not a failure either
        # (issue #801): `queued-alarm` #87/#88 went red mid-sweep — 14 minutes into the
        # very delivery (15:19Z, run 43049550731) that succeeded at 19:03Z. In flight is
        # PENDING until the cap; past the cap a run that never concludes is HUNG.
        if conclusion in INFLIGHT_CONCLUSIONS:
            if age <= inflight_cap_hours:
                return {"pending": True,
                        "reason": (f"the newest delivery started {age:.1f} h ago and is still "
                                   f"'{conclusion}' — in flight, so it has delivered no verdict "
                                   f"(the next alarm delivery re-grades it)"),
                        "age_hours": round(age, 2), "newest": newest["at"],
                        "conclusion": conclusion, "missed": 0, "gaps": gaps[:6],
                        "url": newest.get("url")}
            return {"reason": (f"the newest delivery started {age:.1f} h ago and is STILL "
                               f"'{conclusion}' past the {inflight_cap_hours} h in-flight cap — "
                               f"a sweep that never concludes delivered nothing"),
                    "hung": True, "age_hours": round(age, 2), "newest": newest["at"],
                    "conclusion": conclusion, "missed": 0, "gaps": gaps[:6],
                    "url": newest.get("url")}
        return {"reason": (f"the newest delivery is only {age:.1f} h old but concluded "
                           f"'{conclusion}' — a sweep that ran and did not "
                           f"succeed delivered nothing"),
                "age_hours": round(age, 2), "newest": newest["at"],
                "conclusion": conclusion, "missed": 0, "gaps": gaps[:6],
                "url": newest.get("url"), "fresh": True}
    if not scheduled:
        conclusion = newest.get("conclusion")
        if conclusion == "success":
            # A dispatch-only sweep owes no slot: old-but-green is not a failure (issue #1029).
            return None
        # Old AND not green is still loud: a dispatch that died (or never concluded) is
        # exactly what this alarm exists for.
        return {"reason": (f"the newest dispatch is {age:.1f} h old and concluded "
                           f"'{conclusion}' — a dispatch-only sweep that never delivered a "
                           f"green run is loud (issue #1029)"),
                "age_hours": round(age, 2), "newest": newest["at"], "conclusion": conclusion,
                "missed": None, "gaps": gaps[:6], "url": newest.get("url"),
                "hung": conclusion in INFLIGHT_CONCLUSIONS}
    return {"reason": f"the newest delivery is {age:.1f} h old (max {max_age_hours} h)",
            "age_hours": round(age, 2), "newest": newest["at"], "conclusion": newest["conclusion"],
            "missed": missed_slots(newest["at"], now), "gaps": gaps[:6], "url": newest["url"]}


def render_pending(verdict: dict) -> str:
    """The mid-flight verdict, printed as PENDING so it is never read as health or as a drop."""
    lines = [f"[sweep-alarm] PENDING: {verdict['reason']}",
             f"  newest schedule run: {verdict['newest'].strftime('%Y-%m-%dT%H:%M:%SZ')} "
             f"({verdict['conclusion']}) — in flight (issue #801), re-graded by the next "
             f"alarm delivery",
             f"  it is NOT a failure: no conclusion has been delivered yet"]
    if verdict.get("url"):
        lines.append(f"  run in flight: {verdict['url']}")
    return "\n".join(lines)


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
        f"every Wednesday)",
    ]
    if verdict.get("gaps"):
        lines.append("  gaps between the deliveries it can see: "
                     + ", ".join(f"{g} h" for g in verdict["gaps"]))
    if verdict.get("hung"):
        lines.append("  the delivery is HUNG: still running past the in-flight cap — a sweep "
                     "that never concludes drains no queue (issue #801)")
    elif verdict["conclusion"] not in ("success", None):
        lines.append(f"  the LAST delivery was {verdict['conclusion']} — a sweep that is red on "
                     f"every run looks the same as a missing one from here")
    if verdict.get("fresh"):
        lines.append("  the delivery is FRESH: this is not a dropped cron, it is a sweep that "
                     "ran and did not succeed (issue #498) — the queue did not drain")
    lines += [
        f"  the weekly queue is not being drained at one issue per Wednesday; MAX_AGE_HOURS="
        f"{max_age_hours}",
        "  a dropped cron has no run to look at — that is why this reads the ARTIFACT (issue #497)",
    ]
    if verdict.get("url"):
        lines.append(f"  last run: {verdict['url']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Fail loudly when the weekly sweep has not been DELIVERED (issue #497)")
    ap.add_argument("--repo", required=True, help="owner/name")
    ap.add_argument("--max-age-hours", type=float, default=168.0,
                    help="how stale the newest delivery may be (default 168 — one weekly "
                         "sweep slot plus grace; issue #804)")
    ap.add_argument("--inflight-cap-hours", type=float, default=3.0,
                    help="how long a delivery may be in flight before it is HUNG (issue #801)")
    ap.add_argument("--now", default=None, help="Iso8601 instant to measure from (tests)")
    ap.add_argument("--limit", type=int, default=20, help="how many deliveries to read")
    ap.add_argument("--workflows-dir", default=str(ROOT / ".github" / "workflows"),
                    help="the workflows tree that decides whether the sweep is scheduled "
                         "(issue #1029)")
    args = ap.parse_args(argv)

    now = _ts(args.now) or dt.datetime.now(dt.timezone.utc)
    try:
        scheduled = workflow_declares_schedule(Path(args.workflows_dir))
    except OSError as exc:
        print(f"[sweep-alarm] FAIL: cannot read the sweep workflow to decide the mode: {exc}",
              file=sys.stderr)
        return 2
    try:
        rows = deliveries(args.repo, args.limit)
    except (RuntimeError, ValueError) as exc:
        print(f"[sweep-alarm] FAIL: {exc}", file=sys.stderr)
        return 2

    verdict = stale(rows, now, args.max_age_hours, args.inflight_cap_hours, scheduled)
    if verdict is None:
        if not rows:
            print("[sweep-alarm] OK: dispatch-only sweep (issue #1029) — no delivery is owed")
            return 0
        newest = rows[0]
        mode = ("schedule delivery" if scheduled
                else "dispatch (dispatch-only sweep, #1029)")
        print(f"[sweep-alarm] OK: newest {mode} "
              f"{newest['at'].strftime('%Y-%m-%dT%H:%M:%SZ')} ({newest['conclusion']})"
              + (f", within {args.max_age_hours} h" if scheduled else ""))
        return 0
    if verdict.get("pending"):
        print(render_pending(verdict))
        return 0
    print(render(verdict, rows, args.max_age_hours))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
