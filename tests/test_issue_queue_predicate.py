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


def _stub_gh(tmp: Path, body: str, state: str = "OPEN") -> None:
    """A stub GitHub CLI. Only the external system is faked; the product code runs.

    `state` defaults to gh's REAL spelling `OPEN` (issue #1318): the previous default was
    lowercase `open`, which is why this suite passed while the shipped predicate — comparing
    `== "open"` — never matched a real `gh pr list` answer and the #1310 fix was inert.
    """
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
        _stub_gh(Path(d), "closes #1176", state="CLOSED")
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


def _stub_gh_window(tmp: Path) -> None:
    """A stub `gh` with 100 newer CLOSED PRs + one older OPEN closing PR (#1324).

    Only the external GitHub CLI is faked (rule 6m): the stub honours `--state`
    and `--limit` and orders newest-first, exactly as `gh pr list` does. `_pulls`
    must still receive the live OPEN PR; a `--state all --limit 100` caller sees
    only the 100 closed rows and loses it.
    """
    bin_dir = tmp / "bin"
    bin_dir.mkdir()
    script = bin_dir / "gh"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "a = sys.argv[1:]\n"
        "closed = [{'number': 1000 + i, 'headRefName': 'fix/closed-%d' % i,\n"
        "           'state': 'CLOSED', 'createdAt': '2026-11-22T10:00:00Z',\n"
        "           'updatedAt': '2026-11-22T18:00:00Z', 'body': 'closes #1176'}\n"
        "          for i in range(100)]\n"
        "live = {'number': 42, 'headRefName': 'fix/pr-block-grace-derived-1176',\n"
        "        'state': 'OPEN', 'createdAt': '2026-11-20T11:52:00Z',\n"
        "        'updatedAt': '2026-11-20T12:13:00Z', 'body': 'closes #1176'}\n"
        "rows = closed + [live]\n"
        "state = a[a.index('--state') + 1] if '--state' in a else 'all'\n"
        "if state != 'all':\n"
        "    rows = [r for r in rows if r['state'].lower() == state]\n"
        "rows.sort(key=lambda r: r['updatedAt'], reverse=True)\n"
        "limit = int(a[a.index('--limit') + 1]) if '--limit' in a else 100\n"
        "rows = rows[:limit]\n"
        "if a[:1] == ['pr'] and 'list' in a:\n"
        "    print(json.dumps(rows))\n"
        "else:\n"
        "    print('[]')\n",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    os.environ["PATH"] = f"{bin_dir}:{os.environ['PATH']}"


def test_an_open_closing_pr_survives_a_window_of_closed_prs() -> None:
    """Issue #1324: 100 newer closed PRs must not crowd a live OPEN PR out."""
    with tempfile.TemporaryDirectory() as d:
        _stub_gh_window(Path(d))
        pulls = q._pulls("andyholst/trending-local-llms")
        check("_pulls asks gh only for OPEN PRs",
              any(p.get("number") == 42 for p in pulls),
              "the live closing PR was crowded out: " + str([p.get("number") for p in pulls[:3]]))


def test_the_one_closure_parser_is_used_not_a_hand_rolled_regex() -> None:
    check("a closes keyword binds", q._closes_issue({"body": "closes #1176"}, 1176))
    check("Fixes binds too", q._closes_issue({"body": "Fixes #1176"}, 1176))
    check("another issue does not bind", not q._closes_issue({"body": "closes #1175"}, 1176))
    check("a code-quoted keyword is prose",
          not q._closes_issue({"body": "an example: `closes #1176` in docs"}, 1176))
    check("an absent body does not bind", not q._closes_issue({}, 1176))


def test_the_queue_plants_ghs_real_open_spelling() -> None:
    """Issue #1318: the fixture carries gh's REAL `OPEN`, and the seam is case-blind.

    The previous fixture defaulted to lowercase `open`, so this suite passed while the
    shipped `== "open"` comparison never matched a real `gh pr list` answer — the #1310
    fix was inert in production.
    """
    src = Path(__file__).read_text(encoding="utf-8")
    check("the stub plants gh's real OPEN spelling, not a lowercase-only fixture",
          'state: str = "OPEN"' in src, "")
    is_open = getattr(q, "_is_open", None)
    check("the queue has ONE case-insensitive open-state helper", is_open is not None, "")
    if is_open is None:  # the base script: refuse cleanly, never abort the module
        return
    check("OPEN counts as open", is_open({"state": "OPEN"}))
    check("a lowercase open counts as open too", is_open({"state": "open"}))
    check("CLOSED does not count as open", not is_open({"state": "CLOSED"}))
    check("an absent pull is not open", not is_open(None))
    seam = (ROOT / "scripts" / "issue_queue.py").read_text(encoding="utf-8")
    check("the PR-state test is ONE case-insensitive helper, not two comparisons",
          seam.count('get("state")') == 1 and "def _is_open" in seam, "")


def main() -> int:
    test_a_fix_prefixed_closing_pr_is_an_implementer()
    test_a_pr_without_a_closing_binding_stays_in_the_queue()
    test_a_closed_closing_pr_does_not_mark_implementer()
    test_a_pr_closing_another_issue_does_not_hide_this_one()
    test_an_open_closing_pr_survives_a_window_of_closed_prs()
    test_the_one_closure_parser_is_used_not_a_hand_rolled_regex()
    test_the_queue_plants_ghs_real_open_spelling()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
