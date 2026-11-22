#!/usr/bin/env python3
"""The implementer queue must see an open PR that closes an issue on ANY branch (issue #1310).

`issue_queue.build` used to count only a `ci/data-gap-<n>-*` branch and a PR whose
`headRefName` equalled it. An agent-owned PR cut as `fix/`, `feat/` or `rule/` was
invisible, so an already-implemented issue was offered to the next sweep as
`next-sweep`. These tests drive the REAL queue seam against a stub `gh` (the only
stand-in is the external GitHub CLI, rule 6m) and the REAL closure parser.

Run standalone: python3 tests/test_issue_queue_predicate.py   or   make test
"""
from __future__ import annotations

import datetime as dt
import json
import os
import stat
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import issue_queue as q  # noqa: E402

_PASS = 0
_FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global _PASS, _FAIL
    if ok:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"FAIL: {name} {detail}")


def _stub_gh(tmp: Path, body: str, state: str = "open") -> None:
    """A stub GitHub CLI. Only the external system is faked; the product code runs."""
    bin_dir = tmp / "bin"
    bin_dir.mkdir()
    script = bin_dir / "gh"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "a = sys.argv[1:]\n"
        "joined = ' '.join(a)\n"
        f"PR_BODY = {json.dumps(body)}\n"
        "if a[:1] == ['pr'] and 'list' in a:\n"
        "    print(json.dumps([{'number': 42, 'headRefName': 'fix/pr-block-grace-derived-1176',\n"
        "                       'state': " + repr(state) + ",\n"
        "                       'createdAt': '2026-11-22T11:52:00Z',\n"
        "                       'updatedAt': '2026-11-22T12:13:00Z', 'body': PR_BODY}]))\n"
        "elif a[:1] == ['issue'] and 'list' in a:\n"
        "    print(json.dumps([{'number': 1176, 'createdAt': '2026-11-20T13:50:49Z',\n"
        "                       'labels': [{'name': 'tech-debt'}]}]))\n"
        "else:\n"
        "    print('[]')\n",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    os.environ["PATH"] = f"{bin_dir}:{os.environ['PATH']}"


def test_a_fix_prefixed_closing_pr_is_an_implementer() -> None:
    with tempfile.TemporaryDirectory() as d:
        _stub_gh(Path(d), "Implemented the derived grace.\n\ncloses #1176\n")
        rows = q.build("andyholst/trending-local-llms", "tech-debt", 3,
                       dt.datetime(2026, 11, 22, 15, 0, tzinfo=dt.timezone.utc))
        check("a fix/-prefixed closing PR removes the issue from the queue",
              all(r["issue"] != 1176 for r in rows), str(rows))


def test_a_pr_without_a_closing_binding_stays_in_the_queue() -> None:
    with tempfile.TemporaryDirectory() as d:
        _stub_gh(Path(d), "Related work on the grace window, not closing it.")
        rows = q.build("andyholst/trending-local-llms", "tech-debt", 3,
                       dt.datetime(2026, 11, 22, 15, 0, tzinfo=dt.timezone.utc))
        check("an unbound PR does not mark the issue as implemented",
              any(r["issue"] == 1176 and r["has_implementer"] == 0 for r in rows), str(rows))


def test_a_closed_closing_pr_does_not_mark_implementer() -> None:
    with tempfile.TemporaryDirectory() as d:
        _stub_gh(Path(d), "closes #1176", state="closed")
        rows = q.build("andyholst/trending-local-llms", "tech-debt", 3,
                       dt.datetime(2026, 11, 22, 15, 0, tzinfo=dt.timezone.utc))
        check("a closed PR with a closing keyword is not live implementer",
              any(r["issue"] == 1176 and r["has_implementer"] == 0 for r in rows), str(rows))


def test_a_pr_closing_another_issue_does_not_hide_this_one() -> None:
    # The parser unit test below proves "closes #1175" does not bind #1176; this
    # proves build() actually USES that binding per issue. A regression to "any
    # closing keyword marks an implementer" would silently drop #1176 here.
    with tempfile.TemporaryDirectory() as d:
        _stub_gh(Path(d), "closes #1175")
        rows = q.build("andyholst/trending-local-llms", "tech-debt", 3,
                       dt.datetime(2026, 11, 22, 15, 0, tzinfo=dt.timezone.utc))
        check("a PR closing another issue does not mark this one implemented",
              any(r["issue"] == 1176 and r["has_implementer"] == 0 for r in rows), str(rows))


def test_the_one_closure_parser_is_used_not_a_hand_rolled_regex() -> None:
    check("a closes keyword binds", q._closes_issue({"body": "closes #1176"}, 1176))
    check("Fixes binds too", q._closes_issue({"body": "Fixes #1176"}, 1176))
    check("another issue does not bind", not q._closes_issue({"body": "closes #1175"}, 1176))
    check("a code-quoted keyword is prose",
          not q._closes_issue({"body": "an example: `closes #1176` in docs"}, 1176))
    check("an absent body does not bind", not q._closes_issue({}, 1176))


def main() -> int:
    test_a_fix_prefixed_closing_pr_is_an_implementer()
    test_a_pr_without_a_closing_binding_stays_in_the_queue()
    test_a_closed_closing_pr_does_not_mark_implementer()
    test_a_pr_closing_another_issue_does_not_hide_this_one()
    test_the_one_closure_parser_is_used_not_a_hand_rolled_regex()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
