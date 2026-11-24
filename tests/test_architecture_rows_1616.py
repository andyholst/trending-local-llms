#!/usr/bin/env python3
"""`ARCHITECTURE.md` carries #1616's push-proves-CI rows (issue #1648).

PR #1631 (`fix/auto-merge-rebase-ci-schedules-1616`) documents the contract it
lands — `rebased=true` (the verdict that skips qa-validate's squash) is
reported ONLY after the PUSHED sha's OWN `qa-validate.yml` run is read back
from GitHub and found to carry >0 jobs — in four hand-written rows: the
`auto-merge-rebase` target row, the qa-validate `auto-merge` job row, and the
`scripts/pr_health.py` / `scripts/auto_merge_rebase.py` script rows.

The latest rebase onto `origin/master` resolved an `ARCHITECTURE.md` conflict
by taking master's side and silently dropped all four clauses: measured, head
`5eea2616` carried them while head `460f7100` had
`git show <head>:ARCHITECTURE.md | grep -c 1616` = 0, no `ARCHITECTURE.md`
entry in `gh pr diff 1631`, and a tree byte-identical to master's — yet the
PR body still claimed the rows (issue #1648).

This guard reads the REAL `ARCHITECTURE.md` — no fixture, no stand-in
(rule 6m) — and asserts each clause sits in ITS OWN row, so a later edit or
rebase that re-words or drops one of them reds here. It is RED on the
pre-repair tree by design (master names no #1616 clause at all).

Run:  python3 tests/test_architecture_rows_1616.py   or   make test
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "ARCHITECTURE.md"

#: (row key, verbatim #1616 clause that must sit in that row). A clause that
#: moved to another row — or vanished — is a failure, not a substring match.
ROWS: tuple[tuple[str, str], ...] = (
    (
        "| `auto-merge-rebase` (`PR=<n>` `REPO=<owner/name>`) |",
        "Since issue #1616 the rebase is reported (`rebased=true`, the verdict "
        "that skips the squash) ONLY after reading the PUSHED sha's own "
        "`qa-validate.yml` run back from GitHub and finding >0 jobs",
    ),
    (
        "| `auto-merge` |",
        "Since issue #1616 the rebase is reported (`rebased=true`, which skips "
        "THIS run's squash) only after the pushed sha's OWN qa-validate run is "
        "read back with >0 jobs",
    ),
    (
        "| `scripts/pr_health.py` |",
        "Since issue #1616 every pushed head's OWN `qa-validate.yml` run is "
        "read back (`verify_rebased_ci`, through the ONE gh field contract)",
    ),
    (
        "| `scripts/auto_merge_rebase.py` |",
        "since #1616 reads the pushed sha's own run back for its CI proof",
    ),
    (
        "| `scripts/auto_merge_rebase.py` |",
        "a push that landed without scheduling real CI is `verdict=ci-unverified`, "
        "`rebased=false`, exit 1",
    ),
)

_PASS = 0
_FAIL = 0


def check(name: str, cond: bool, detail: object = "") -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def _row(lines: list[str], key: str) -> str | None:
    """The ONE line starting with `key`, or None unless it is unambiguous."""
    hits = [line for line in lines if line.startswith(key)]
    return hits[0] if len(hits) == 1 else None


def test_the_push_proves_ci_rows_still_name_issue_1616() -> None:
    """Every #1616 contract row survives — the #1648 rebase-drop regression."""
    text = DOC.read_text(encoding="utf-8")
    lines = text.splitlines()
    check("ARCHITECTURE.md is readable", bool(text.strip()), f"{DOC} empty")
    for key, clause in ROWS:
        row = _row(lines, key)
        label = key.strip("| ").split("`")[1] if "`" in key else key
        check(f"row `{label}` exists exactly once", row is not None,
              f"hits={sum(1 for line in lines if line.startswith(key))}")
        if row is None:
            continue
        check(f"row `{label}` still names the #1616 push-proves-CI clause",
              clause in row, clause[:70])


def main() -> int:
    print("ARCHITECTURE.md #1616 push-proves-CI rows (rule 6h, issue #1648)")
    test_the_push_proves_ci_rows_still_name_issue_1616()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
