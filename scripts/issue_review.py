#!/usr/bin/env python3
"""The issue reviewer's deterministic core (issue #179).

The LLM does the judgement — refine the body, classify, write the reminders —
and NEVER the dispatching. This script owns the part that must be exact:

    --pick                 ONE issue per run: the oldest candidate whose
                           implementer window is CLOSED (path `body`), else the
                           oldest candidate whose window is open because an
                           implementer has STARTED and the reviewer has not
                           replied yet (path `window`), else `action=none`.
    --mark ISSUE --path P  open the reviewer's window: the `review-in-progress`
                           label (so `issue-bot`'s pick defers to us) + the
                           marker comment for `body`; prints `marker_iso` and
                           the body hash the run started from.
    --guard ISSUE --for P  the TOCTOU re-check, run AFTER the mark and BEFORE
                           anything is written: exit 0 only while the guard for
                           that path still holds (window still closed for a body
                           rewrite; still wanted, and no reply yet, for a reply).
    --body-hash ISSUE      the current body hash: the run proves it did NOT edit
                           the body on the `window` path.
    --finish ISSUE         close the reviewer's window (remove the label).

One queue, one window definition: this module imports `issue_queue` — the SAME
rule `issue-bot`'s `pick` reads (AGENTS.md rule 6d, "no second implementation").

Usage:
    python3 scripts/issue_review.py --pick [--repo R] [--now ISO] [--gap-hours 3]
    python3 scripts/issue_review.py --mark 163 --path body
    python3 scripts/issue_review.py --guard 163 --for body
    python3 scripts/issue_review.py --body-hash 163
    python3 scripts/issue_review.py --finish 163
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import issue_queue as iq  # noqa: E402  (one queue, one window — rule 6d)

REVIEW_LABEL = iq.REVIEW_LABEL
LABEL_DESCRIPTION = "An issue reviewer is working this issue (issue-bot defers to it)"
LABEL_COLOR = "FBCA04"


def _gh(args: list[str], check: bool = True) -> str:
    proc = subprocess.run(["gh", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        if check:
            raise SystemExit(f"[issue-review] gh {' '.join(args)} failed: {proc.stderr.strip()}")
        return ""
    return proc.stdout


def body_sha(repo: str, number: int) -> str:
    out = _gh(["api", f"repos/{repo}/issues/{number}", "--jq", ".body"], check=False)
    return hashlib.sha256((out or "").encode()).hexdigest()


def ensure_label(repo: str) -> None:
    listed = _gh(["label", "list", "--repo", repo, "--search", REVIEW_LABEL, "--json", "name"], check=False)
    try:
        names = {l["name"] for l in json.loads(listed or "[]")}
    except json.JSONDecodeError:
        names = set()
    if REVIEW_LABEL in names:
        return
    _gh(["label", "create", REVIEW_LABEL, "--repo", repo, "--color", LABEL_COLOR,
         "--description", LABEL_DESCRIPTION], check=False)


def pick(rows: list[dict]) -> dict:
    """The oldest reviewable candidate; else the one implementing; else nothing."""
    for row in rows:
        if row["window"] == "closed" and not row["review_recent"]:
            return {"action": "review", "issue": row["issue"], "path": "body", "reason": "window-closed"}
    for row in rows:
        if row["window"] == "open" and row["started"] and not row["reply_recent"]:
            return {"action": "window", "issue": row["issue"], "path": "window", "reason": row["reason"]}
    return {"action": "none", "issue": "", "path": "", "reason": "all-deferred"}


def row_for(rows: list[dict], number: int) -> dict | None:
    return next((r for r in rows if r["issue"] == number), None)


def decide(repo: str, gap_hours: int, now: dt.datetime,
           run: str | None = None) -> tuple[dict, list[dict]]:
    rows = iq.build(repo, "data-gap-analysis", gap_hours, now, run or iq.current_run())
    return pick(rows), rows


def _print_action(decision: dict) -> None:
    print(f"action={decision['action']}")
    print(f"issue={decision['issue']}")
    print(f"path={decision['path']}")
    print(f"reason={decision['reason']}")


def cmd_pick(repo: str, gap_hours: int, now: dt.datetime, run: str | None = None) -> int:
    decision, rows = decide(repo, gap_hours, now, run)
    for row in rows:
        print(f"issue={row['issue']} position={row['position']} window={row['window']} "
              f"reason={row['reason']} started={row['started']} reply_recent={row['reply_recent']} "
              f"review_recent={row['review_recent']}")
    _print_action(decision)
    return 0


def cmd_mark(repo: str, number: int, path: str, now: dt.datetime,
             run: str | None = None) -> int:
    ensure_label(repo)
    _gh(["issue", "edit", str(number), "--repo", repo, "--add-label", REVIEW_LABEL], check=False)
    marker = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    if path == "body":
        # The run id is what stops this run from blocking its OWN guard re-check,
        # and what tells the next run (and the implementer) that a review is live.
        rendered = f"<!-- issue-review: {marker} run={run or iq.current_run()} -->"
        _gh(["issue", "comment", str(number), "--repo", repo, "--body", rendered])
    print(f"marker_iso={marker}")
    print(f"body_sha={body_sha(repo, number)}")
    return 0


def cmd_guard(repo: str, number: int, for_path: str, gap_hours: int, now: dt.datetime,
              run: str | None = None) -> int:
    """Exit 0 only while the reviewer may still act. Run it right before the write."""
    _, rows = decide(repo, gap_hours, now, run)
    row = row_for(rows, number)
    if row is None:
        print("guard=blocked reason=not-a-candidate")
        return 1
    if for_path == "body":
        # A review from ANOTHER run in flight first: that is the reason a reviewer
        # reading the log needs, not the generic "window open".
        if row["review_recent"]:
            print("guard=blocked reason=reviewed-recently")
            return 1
        if row["window"] != "closed":
            print(f"guard=blocked reason=window-open:{row['reason']}")
            return 1
        print("guard=ok path=body")
        return 0
    if row["window"] != "open":
        print("guard=blocked reason=window-closed")
        return 1
    if not row["started"]:
        print(f"guard=blocked reason=not-started:{row['reason']}")
        return 1
    if row["reply_recent"]:
        print("guard=blocked reason=already-replied-in-this-window")
        return 1
    print(f"guard=ok path=window reason={row['reason']}")
    return 0


def cmd_body_hash(repo: str, number: int) -> int:
    print(f"body_sha={body_sha(repo, number)}")
    return 0


COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def cmd_check_markers(repo: str, number: int, path: str) -> int:
    """The rewrite keeps every invisible marker: a dropped one re-files an issue.

    `<!-- data-gap-signature: … -->` (scripts/data_gap_analysis.py) and
    `<!-- tech-debt-signature: … -->` (scripts/file_findings.py) are the two the
    chains dedup on — a body rewrite that loses one files the SAME gap or finding
    again (measured on #184/#185). The reviewer may add sections around them; it
    may never remove one.
    """
    target = Path(path) if path else None
    if target is None or not target.is_file():
        print(f"markers=ERROR file-missing:{path}")
        return 1
    current = _gh(["api", f"repos/{repo}/issues/{number}", "--jq", ".body"], check=False)
    before = [m.strip() for m in COMMENT_RE.findall(current or "")]
    after = [m.strip() for m in COMMENT_RE.findall(target.read_text(encoding="utf-8"))]
    missing = [m for m in before if m not in after]
    if missing:
        print(f"markers=MISSING {' | '.join(missing)}")
        return 1
    print(f"markers=ok kept={len(before)}")
    return 0


def cmd_finish(repo: str, number: int) -> int:
    _gh(["issue", "edit", str(number), "--repo", repo, "--remove-label", REVIEW_LABEL], check=False)
    print(f"finished={number}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="The issue reviewer's deterministic core (issue #179)")
    ap.add_argument("--repo", default=None)
    ap.add_argument("--now", default=None)
    ap.add_argument("--gap-hours", type=int, default=int(os.environ.get("REVIEW_GAP_HOURS", "3")))
    ap.add_argument("--run", default=None, help="this run's id (a run never blocks itself)")
    ap.add_argument("--pick", action="store_true")
    ap.add_argument("--mark", type=int, metavar="ISSUE")
    ap.add_argument("--guard", type=int, metavar="ISSUE")
    ap.add_argument("--body-hash", type=int, metavar="ISSUE")
    ap.add_argument("--check-markers", type=int, metavar="ISSUE",
                    help="fail when FILE= (the rewritten body) dropped an invisible marker")
    ap.add_argument("--file", default="issue-body.md", help="--check-markers: the rewritten body")
    ap.add_argument("--finish", type=int, metavar="ISSUE")
    ap.add_argument("--path", choices=["body", "window"], default="body",
                    help="--mark: which window the reviewer is opening")
    ap.add_argument("--for", dest="for_path", choices=["body", "window"], default="body",
                    help="--guard: which path is being re-checked")
    args = ap.parse_args(argv)

    repo = iq.resolve_repo(args.repo)
    now = iq.now_utc(args.now)

    if args.pick:
        return cmd_pick(repo, args.gap_hours, now, args.run)
    if args.mark:
        return cmd_mark(repo, args.mark, args.path, now, args.run)
    if args.guard:
        return cmd_guard(repo, args.guard, args.for_path, args.gap_hours, now, args.run)
    if args.body_hash:
        return cmd_body_hash(repo, args.body_hash)
    if args.check_markers:
        return cmd_check_markers(repo, args.check_markers, args.file)
    if args.finish:
        return cmd_finish(repo, args.finish)
    ap.error("nothing to do: pass --pick, --mark, --guard, --body-hash or --finish")
    return 2


if __name__ == "__main__":
    sys.exit(main())
