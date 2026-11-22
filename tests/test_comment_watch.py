#!/usr/bin/env python3
"""tests/test_comment_watch.py — issue #1243.

The comment watcher is a read-only `gh` trigger: new comments on any trending-local-llms
issue/PR must be LOOKed at, answered, filed as new work when needed, and implemented.
This suite injects gh output (no network) and reads the REAL rulebook/Makefile so a
dropped rule or target binding is a named finding.
"""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import comment_watch as CW  # noqa: E402
from wiring import wired  # noqa: E402

_PASS = 0
_FAIL = 0


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


NOW = datetime(2026, 11, 22, 3, 0, 0, tzinfo=timezone.utc)
COMMENTS = [
    {"created_at": "2026-11-22T02:30:00Z", "user": {"login": "other-machine"},
     "body": "please look at the index drift", "issue_url": "https://api.github.com/repos/x/issues/999",
     "html_url": "https://github.com/x/issues/999"},
    {"created_at": "2026-11-20T01:00:00Z", "user": {"login": "other-machine"},
     "body": "too old", "issue_url": "https://api.github.com/repos/x/issues/998", "html_url": ""},
    {"created_at": "2026-11-22T02:45:00Z", "user": {"login": "asimov"},
     "body": "my own note", "issue_url": "https://api.github.com/repos/x/issues/997", "html_url": ""},
]


def test_watcher():
    check("a fresh checkout watches the last day", CW.default_since(NOW).startswith("2026-11-21"))
    calls = []

    def fake_runner(cmd):
        calls.append(cmd)
        return json.dumps(COMMENTS)

    got = CW.gh_comments("andyholst/trending-local-llms", "2026-11-21T03:00:00Z", fake_runner)
    check("gh api is the ONE read seam", len(got) == 3 and calls[0][:2] == ["gh", "api"] and
          calls[0][2].startswith("repos/andyholst/trending-local-llms/issues/comments?"), str(calls[0]))
    check("the cursor is sent to gh", "since=2026-11-21T03%3A00%3A00Z" in calls[0][2], str(calls[0]))
    fresh = CW.unseen(got, "2026-11-21T03:00:00Z", {"asimov"})
    check("self-authored and older comments are ignored", [c["body"] for c in fresh] == ["please look at the index drift"], str(fresh))
    shown = CW.render(fresh)
    check("the event names the thread and author", "issue_or_pr=999" in shown and "other-machine" in shown, shown)
    with tempfile.TemporaryDirectory() as td:
        state = Path(td) / "cursor.json"
        CW.save_cursor(state, "2026-11-22T02:30:00Z")
        CW.save_cursor(state, "2026-11-22T01:00:00Z")  # late page must not rewind
        check("the cursor never moves backwards", CW.load_cursor(state, NOW) == "2026-11-22T02:30:00Z")


def test_rulebook():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    a = text.find("6w. Comments are a trigger")
    rule = text[a:text.find("## 3. Data source & collection", a)] if a >= 0 else ""
    clauses = {
        "watcher named": "make comment-watch",
        "full-thread reading": "READ the full thread with `gh issue view`",
        "LOOK duty": "LOOK at what was said",
        "reply duty": "post a reply on that thread",
        "new issue duty": "file a new issue for any NEW work",
        "implement duty": "implement that work in a",
        "mark-read honesty": "never acknowledge a comment unseen",
        "owner-only boundary": "grants access; those stay\n   owner-only",
        "regression test named": "tests/test_comment_watch.py",
    }
    check("AGENTS.md carries rule 6w", bool(rule))
    for name, needle in clauses.items():
        check(f"rule keeps {name}", needle in rule, name)
    planted = rule.replace("never acknowledge a comment unseen", "acknowledge before looking")
    check("a planted omission is named by the guard",
          "never acknowledge a comment unseen" not in planted)
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    check("make comment-watch is bound to the watcher",
          "comment-watch:" in makefile and "scripts/comment_watch.py" in makefile)
    check("this suite is discovered by `make test`", wired(__file__))


def main() -> int:
    print("comment-watch trigger (issue #1243):")
    test_watcher()
    test_rulebook()
    print(f"{'FAILED' if _FAIL else 'PASSED'} {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
