#!/usr/bin/env python3
"""scripts/comment_monitor.py -- issue #1243.

The deterministic change-detector used by the Hermes cron trigger. It prints ONLY
the sorted IDs of comments newer than the local cursor, so an unchanged tick skips
the agent and a new comment wakes it. Every author counts, including our own agent
identity: a test comment from asimov-agent must trigger the watcher.

No timestamps or random ordering in stdout (the scheduler hashes exact bytes).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from urllib.parse import urlencode

DEFAULT_REPO = "andyholst/trending-local-llms"
DEFAULT_CURSOR = Path(".local/comment-watch.json")
IGNORE: set[str] = set()  # notify on EVERY new comment, including our own agent identity


def since(cursor_file: Path) -> str:
    if cursor_file.exists():
        try:
            value = str(json.loads(cursor_file.read_text(encoding="utf-8")).get("since") or "")
            if value:
                return value
        except (ValueError, OSError):
            pass
    # Without a cursor, `issues/comments?per_page=100&direction=asc` returns the
    # OLDEST 100 comments — fresh ones never appear. Baseline ONCE to the last 24h.
    from datetime import datetime, timedelta, timezone
    default = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    cursor_file.parent.mkdir(parents=True, exist_ok=True)
    cursor_file.write_text(json.dumps({"since": default}) + "\n", encoding="utf-8")
    return default


def comment_ids(repo: str, cursor: str, runner, page_limit: int = 20) -> list[str]:
    """The ONE read seam; page until the cursor is reached (newest-first)."""
    ids: set[str] = set()
    oldest_seen = ""
    for page in range(1, page_limit + 1):
        query = urlencode({"per_page": 100, "sort": "created", "direction": "desc",
                           "page": page})
        if cursor:
            query += "&since=" + cursor
        raw = runner(["gh", "api", f"repos/{repo}/issues/comments?{query}"])
        try:
            batch = json.loads(raw or "[]")
        except ValueError:
            batch = []
        if not isinstance(batch, list) or not batch:
            break
        for c in batch:
            if not isinstance(c, dict):
                continue
            created = str(c.get("created_at") or "")
            if created and (not oldest_seen or created < oldest_seen):
                oldest_seen = created
            if (created > cursor and
                    str((c.get("user") or {}).get("login") or "") not in IGNORE):
                ids.add(str(c.get("id")))
        if len(batch) < 100 or (cursor and oldest_seen and oldest_seen <= cursor):
            break
    return sorted(ids)


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--cursor-file", type=Path,
                    default=Path.home() / ".hermes/profiles/project-manager/cache/scratch/comment-watch-cron.json")
    a = ap.parse_args()
    ids = comment_ids(a.repo, since(a.cursor_file), lambda cmd: subprocess.run(
        cmd, capture_output=True, text=True, check=True, timeout=60).stdout)
    print("\n".join(ids) if ids else "NONE")


if __name__ == "__main__":
    main()
