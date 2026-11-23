#!/usr/bin/env python3
"""scripts/comment_watch.py -- issue #1243.

A deterministic, read-only `gh` comment trigger for the fleet. A new comment on ANY
trending-local-llms issue or PR is an event: the agent must LOOK at the thread, reply
on it, file an issue for new work, and implement it. This tool only REPORTS unseen
comments and advances a LOCAL cursor when --mark-read is given; it never writes to
GitHub, dispatches CI, or changes permissions (owner directive 2026-11-15, rule 6v).

Wake-up markers (C:/R:/M:/H:) are emitted by the ONE canonical detector in
scripts/watch_monitor.py; this module owns only the comment cursor/report half.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_REPO = "andyholst/trending-local-llms"
DEFAULT_STATE = Path(".local/comment-watch.json")


def default_since(now: datetime) -> str:
    """A fresh checkout watches the last 24h, not all of history."""
    return (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_cursor(state_file: Path, now: datetime) -> str:
    if not state_file.exists():
        return default_since(now)
    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return default_since(now)
    return str(data.get("since") or default_since(now))


def save_cursor(state_file: Path, since: str) -> None:
    old = ""
    if state_file.exists():
        try:
            old = str(json.loads(state_file.read_text(encoding="utf-8")).get("since") or "")
        except (ValueError, OSError):
            pass
    # Never move the cursor backwards (a late API page must not replay old events).
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps({"since": max(old, since)}) + "\n", encoding="utf-8")


def gh_comments(repo: str, since: str, runner) -> list[dict]:
    """The ONE `gh api` read; `runner` is injectable so tests need no network."""
    from urllib.parse import urlencode
    query = urlencode({"since": since, "per_page": 100, "sort": "created", "direction": "asc"})
    out = runner([
        "gh", "api", f"repos/{repo}/issues/comments?{query}",
    ])
    payload = json.loads(out or "[]")
    if not isinstance(payload, list):
        raise ValueError("[comment-watch] gh api returned a non-list payload")
    return payload


def unseen(comments: list[dict], since: str, ignore_authors: set[str]) -> list[dict]:
    found = []
    for c in comments:
        created = str(c.get("created_at") or "")
        author = str((c.get("user") or {}).get("login") or "")
        if created <= since or author in ignore_authors:
            continue
        found.append(c)
    return sorted(found, key=lambda c: str(c.get("created_at") or ""))


def issue_number(c: dict) -> str:
    url = str(c.get("issue_url") or "")
    return url.rsplit("/", 1)[-1] if url else "?"


def render(comments: list[dict]) -> str:
    lines = []
    for c in comments:
        first = str(c.get("body") or "").strip().splitlines()
        excerpt = (first[0] if first else "")[:120]
        lines.append(
            f"COMMENT issue_or_pr={issue_number(c)} author={(c.get('user') or {}).get('login', '?')} "
            f"created={c.get('created_at')} url={c.get('html_url')} :: {excerpt}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--state-file", type=Path, default=DEFAULT_STATE)
    ap.add_argument("--ignore-author", dest="ignore_authors", action="append", default=[])
    ap.add_argument("--mark-read", action="store_true",
                    help="advance the local cursor after the comments were LOOKED at and answered")
    a = ap.parse_args(argv)

    now = datetime.now(timezone.utc)
    since = load_cursor(a.state_file, now)
    comments = gh_comments(a.repo, since, lambda cmd: subprocess.run(
        cmd, capture_output=True, text=True, check=True, timeout=60).stdout)
    found = unseen(comments, since, set(a.ignore_authors))
    print(render(found) if found else f"[comment-watch] no comments since {since}")
    if found and a.mark_read:
        save_cursor(a.state_file, str(found[-1]["created_at"]))
        print(f"[comment-watch] cursor advanced to {found[-1]['created_at']} (local only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
