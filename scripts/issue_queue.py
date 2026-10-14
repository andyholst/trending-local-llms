#!/usr/bin/env python3
"""The implementer's queue — ONE implementation, read by both bots (issue #179).

`issue-bot.yml`'s `pick` job chooses ONE issue per sweep: the OLDEST open
`data-gap-analysis` issue that has no implementer yet (no `ci/data-gap-<n>-*`
branch and no open PR from one). The issue reviewer must never refine an issue
inside a window around an implementer start, and the implementer's `pick` must
skip an issue the reviewer is working on — so BOTH bots read the SAME rule from
this ONE script rather than keeping two copies of it in shell and Python
(AGENTS.md rule 6d: one path, no second implementation of the same stage).

What it prints (one line per candidate, in pick order — oldest first):

    issue=<n> position=<i> has_implementer=<0|1> last_implementer_activity=<ISO8601Z|none>
    window=<open|closed>
    reason=<run-in-flight|implementer-recent|next-sweep|reviewer-working|closed>
    started=<0|1> reply_recent=<0|1> review_recent=<0|1> impl_skip=<0|1>

  * `position` — 0-based index in the pick order. The sweep takes ONE issue per
    hour and always the oldest, so `position` IS hours-until-start, which is what
    makes REVIEW_GAP_HOURS measurable as the 3 h *before* a start.
  * `last_implementer_activity` — the newest of: a start comment
    (`<!-- issue-bot-start: <ISO8601Z> -->`, posted by `issue-bot.yml` before it
    implements), its outcome comment ("issue-bot ran for this issue", posted on
    every attempt, `if: always()`), the branch's newest commit, and the PR's
    `createdAt`/`updatedAt`.
  * `window` — `open` while the reviewer must not touch the issue's body:
    an implementer run is in flight (or its start comment is fresh — the comment
    is posted BEFORE `make implement-issue`, so it covers the whole run),
    implementer activity is younger than the gap, or the issue is within the
    next `gap` sweeps. `reason` says which.
  * `started` — an implementer has actually STARTED (as opposed to the issue
    merely being next in line): that is the case where the reviewer posts its
    one bounded reply instead of staying silent.
  * `reply_recent` — the reviewer already replied in this window (the
    `<!-- issue-review: window … -->` marker): one reply per window, never one
    per hour.
  * `review_recent` — the reviewer touched this issue within the gap: its own
    cooldown, so the same issue is not re-refined every hour.

Usage:
    python3 scripts/issue_queue.py [--repo OWNER/NAME] [--now ISO8601] [--gap-hours 3]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys

BRANCH_PREFIX = "ci/data-gap-"
START_MARKER = "<!-- issue-bot-start:"
OUTCOME_TEXT = "issue-bot ran for this issue"
REVIEW_MARKER = "<!-- issue-review:"
WINDOW_REPLY_MARKER = "<!-- issue-review: window"
RUN_ID_RE = re.compile(r"run=([A-Za-z0-9_-]+)")
REVIEW_LABEL = "review-in-progress"
START_TS_RE = re.compile(r"issue-bot-start:\s*([0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9:.]+Z?)")


def _gh(args: list[str], check: bool = True) -> str:
    """Run `gh` and return stdout. A failure is loud unless `check=False`."""
    proc = subprocess.run(["gh", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        if check:
            raise SystemExit(f"[issue-queue] gh {' '.join(args)} failed: {proc.stderr.strip()}")
        return ""
    return proc.stdout


def parse_ts(value: str | None) -> dt.datetime | None:
    """Parse a GitHub ISO timestamp into an aware UTC datetime."""
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def now_utc(value: str | None = None) -> dt.datetime:
    """The clock: injected (`--now` / `ISSUE_REVIEW_NOW`), never the wall clock in tests."""
    injected = value or os.environ.get("ISSUE_REVIEW_NOW")
    parsed = parse_ts(injected)
    return parsed if parsed else dt.datetime.now(dt.timezone.utc)


def current_run() -> str:
    """This workflow run's id (env), or `local` for a hand-run."""
    return os.environ.get("GITHUB_RUN_ID") or "local"


def resolve_repo(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    env = os.environ.get("GITHUB_REPOSITORY") or os.environ.get("REPO")
    if env:
        return env
    out = _gh(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"], check=False)
    if not out.strip():
        raise SystemExit("[issue-queue] no --repo, no GITHUB_REPOSITORY and no gh repo view result")
    return out.strip()


def _issues(repo: str, label: str) -> list[dict]:
    out = _gh(["issue", "list", "--repo", repo, "--label", label, "--state", "open",
               "--limit", "100", "--json", "number,createdAt,labels"])
    items = json.loads(out or "[]")
    return sorted(items, key=lambda i: i.get("createdAt") or "")


def _branches(repo: str) -> set[str]:
    out = _gh(["api", f"repos/{repo}/git/matching-refs/heads/{BRANCH_PREFIX}"], check=False)
    try:
        refs = json.loads(out or "[]")
    except json.JSONDecodeError:
        refs = []
    return {r["ref"].rsplit("/", 1)[-1] for r in refs if isinstance(r, dict) and "ref" in r}


def _pulls(repo: str) -> list[dict]:
    out = _gh(["pr", "list", "--repo", repo, "--state", "all", "--limit", "100",
               "--json", "number,headRefName,state,createdAt,updatedAt"], check=False)
    try:
        return json.loads(out or "[]")
    except json.JSONDecodeError:
        return []


def _runs(repo: str) -> list[dict]:
    out = _gh(["run", "list", "--repo", repo, "--workflow", "issue-bot.yml", "--limit", "30",
               "--json", "databaseId,status,event,createdAt,displayTitle"], check=False)
    try:
        return json.loads(out or "[]")
    except json.JSONDecodeError:
        return []


def _comments(repo: str, number: int) -> list[dict]:
    out = _gh(["api", f"repos/{repo}/issues/{number}/comments?per_page=100",
               "--jq", "[.[] | {createdAt, body}]"], check=False)
    try:
        return json.loads(out or "[]")
    except json.JSONDecodeError:
        return []


def _branch_commit_ts(repo: str, branch: str) -> dt.datetime | None:
    out = _gh(["api", f"repos/{repo}/commits/{branch}", "--jq", ".commit.committer.date"], check=False)
    return parse_ts(out)


def newest(timestamps: list[dt.datetime | None]) -> dt.datetime | None:
    present = [t for t in timestamps if t is not None]
    return max(present) if present else None


def marker_run_id(body: str) -> str | None:
    """The run that wrote a reviewer marker (a run must not block itself)."""
    match = RUN_ID_RE.search(body or "")
    return match.group(1) if match else None


def build(repo: str, label: str, gap_hours: int, now: dt.datetime,
          run: str | None = None) -> list[dict]:
    """Every review candidate, in pick order, with its implementer window.

    `run` is THIS run's id: a reviewer marker this same run wrote is not a
    cooldown against itself (the mark is written before the guard re-checks —
    without this, a run would block its own write).
    """
    refs = _branches(repo)
    pulls = _pulls(repo)
    runs = _runs(repo)
    rows: list[dict] = []
    position = 0

    for issue in _issues(repo, label):
        number = int(issue["number"])
        labels = {l.get("name") for l in issue.get("labels") or []}
        branch = None
        for name in sorted(refs):
            if name.startswith(f"{BRANCH_PREFIX}{number}-"):
                branch = name
                break
        pull = next((p for p in pulls if p.get("headRefName") == branch), None) if branch else None
        has_implementer = bool(branch) or bool(pull and pull.get("state") == "open")
        if has_implementer:
            continue

        comments = _comments(repo, number)
        start_ts = newest([parse_ts(c.get("createdAt")) for c in comments
                           if START_MARKER in (c.get("body") or "")])
        start_marker_ts = newest([parse_ts(m.group(1)) for c in comments
                                  for m in [START_TS_RE.search(c.get("body") or "")] if m])
        outcome_ts = newest([parse_ts(c.get("createdAt")) for c in comments
                             if OUTCOME_TEXT in (c.get("body") or "")])
        review_ts = newest([parse_ts(c.get("createdAt")) for c in comments
                            if REVIEW_MARKER in (c.get("body") or "")
                            and marker_run_id(c.get("body") or "") != run])
        reply_ts = newest([parse_ts(c.get("createdAt")) for c in comments
                           if WINDOW_REPLY_MARKER in (c.get("body") or "")
                           and marker_run_id(c.get("body") or "") != run])
        reviewer_label = REVIEW_LABEL in labels  # advisory; reported, never a hold
        branch_ts = _branch_commit_ts(repo, branch) if branch else None
        pull_ts = newest([parse_ts((pull or {}).get("createdAt")), parse_ts((pull or {}).get("updatedAt"))])
        activity = newest([start_ts, start_marker_ts, outcome_ts, branch_ts, pull_ts])

        def fresh(ts: dt.datetime | None) -> bool:
            return bool(ts) and (now - ts) < dt.timedelta(hours=gap_hours)

        started_recently = fresh(start_ts) or fresh(start_marker_ts)
        # A run we can attribute to THIS issue and that has not finished. The start
        # comment above is the primary signal (it is posted before `make
        # implement-issue`, so it covers the whole run); this is the backstop for a
        # queued run whose start comment the reviewer has not seen yet.
        in_flight = any(
            r.get("status") in ("queued", "in_progress")
            and f"#{number}" in (r.get("displayTitle") or "")
            and fresh(parse_ts(r.get("createdAt")))
            for r in runs
        )
        recent_activity = fresh(activity)
        # The reviewer's own window: a marker from ANOTHER run inside the gap.
        # The `review-in-progress` label alone is NOT enough — labels carry no
        # timestamp, so a label left by a cancelled run would stall the queue for
        # ever; the timestamped marker is what proves a review is live (the
        # workflow removes the label at the end of every run, `always()`).
        reviewer_recent = fresh(review_ts)
        impl_skip = reviewer_recent
        next_sweep = (not impl_skip) and position < gap_hours
        if impl_skip:
            reason = "reviewer-working"
        elif in_flight or started_recently:
            reason = "run-in-flight"
        elif recent_activity:
            reason = "implementer-recent"
        elif next_sweep:
            reason = "next-sweep"
        else:
            reason = "closed"

        label_row = reviewer_label
        row_position = -1 if impl_skip else position
        rows.append({
            "issue": number,
            "position": row_position,
            "has_implementer": 0,
            "last_implementer_activity": activity.strftime("%Y-%m-%dT%H:%M:%SZ") if activity else "none",
            "window": "closed" if reason == "closed" else "open",
            "reason": reason,
            "started": 1 if (in_flight or started_recently) else 0,
            "reply_recent": 1 if fresh(reply_ts) else 0,
            "review_recent": 1 if reviewer_recent else 0,
            "impl_skip": 1 if impl_skip else 0,
            "reviewer_label": 1 if label_row else 0,
            "branch": branch or "",
        })
        if not impl_skip:
            position += 1
    return rows


def render(rows: list[dict]) -> str:
    lines = []
    for r in rows:
        lines.append(
            f"issue={r['issue']} position={r['position']} has_implementer={r['has_implementer']} "
            f"last_implementer_activity={r['last_implementer_activity']} window={r['window']} "
            f"reason={r['reason']} started={r['started']} reply_recent={r['reply_recent']} "
            f"review_recent={r['review_recent']} impl_skip={r['impl_skip']}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="The implementer's queue, for both bots (issue #179)")
    ap.add_argument("--repo", default=None)
    ap.add_argument("--label", default="data-gap-analysis")
    ap.add_argument("--gap-hours", type=int, default=int(os.environ.get("REVIEW_GAP_HOURS", "3")))
    ap.add_argument("--now", default=None)
    ap.add_argument("--run", default=None, help="this run's id (a run never blocks itself)")
    args = ap.parse_args(argv)

    repo = resolve_repo(args.repo)
    now = now_utc(args.now)
    rows = build(repo, args.label, args.gap_hours, now, args.run or current_run())
    text = render(rows)
    if text:
        print(text)
    open_windows = [r for r in rows if r["window"] == "open"]
    print(f"[issue-queue] repo={repo} now={now.strftime('%Y-%m-%dT%H:%M:%SZ')} "
          f"gap={args.gap_hours}h candidates={len(rows)} windows_open={len(open_windows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
