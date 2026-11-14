#!/usr/bin/env python3
"""Fail when the ACTIVE OpenSpec backlog hits its ceiling (issue #938).

`make openspec-check` re-validates EVERY active change on every PR and every
push to master (qa-validate `validate`). The archive lifecycle (#779/#866)
closes a change only through the PR that closes its own issue — and NOTHING
bounds the tail. A stalled issue, a keeper drift or a parked review-required
change stays ACTIVE forever, re-validated on every pipeline while its spec
drifts from the tree; the historical worst measured 84 active on disk (the
stale-index incident recorded in qa-validate.yml).

The owner's directive turns that tail into a hard ceiling: at
MAX_ACTIVE_OPENSPEC_CHANGES active changes the MAIN CI PIPELINE FAILS AT THE
MERGE GATE — the cap check is a prerequisite of `make openspec-check`, which
qa-validate runs on every PR, so nothing auto-merges to `master` until the
backlog is archived. Under the cap it prints `active=<n>/50` so the headroom
is visible long before it goes red; it never archives anything itself
(archiving a change its PR does not close stays the #812-governed act).

Exit codes (the ledger-guard model):
  0  under the cap  — `active=<n>/50` printed
  1  at/over the cap — every active change named with its Issue and remedy
  2  the tree cannot be read — loud, never a vacuous clean

Wired into `make openspec-backlog-check`, a prerequisite of `make
openspec-check` (rules 6d/6m: bundled into the stage the pipeline already runs).

Usage:
    python3 scripts/openspec_backlog_check.py
    python3 scripts/openspec_backlog_check.py --changes-dir <dir>   # fixture seam
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CHANGES_DIR = REPO_ROOT / "openspec" / "changes"

#: The ceiling (issue #938): at this many ACTIVE changes, `openspec-check` —
#: the gate qa-validate runs on every PR — goes red, and auto-merge to master
#: is blocked until the tail is archived. One constant, one implementation.
MAX_ACTIVE_OPENSPEC_CHANGES = 50

_ISSUE_RE = re.compile(r"Issue:\s*(.*#(\d+))", re.IGNORECASE)


def active_changes(changes_dir: Path) -> list[Path]:
    """ACTIVE change directories: everything except `archive/` and dot-dirs."""
    return sorted(p for p in changes_dir.iterdir()
                  if p.is_dir() and p.name != "archive" and not p.name.startswith("."))


def proposal_issue(change: Path) -> str:
    """The `Issue: … #<n>` this change tracks, read from its own proposal.md.

    A change without a proposal (or without an Issue line) is named as such —
    an untracked active change is exactly the drift the cap exists to surface.
    """
    proposal = change / "proposal.md"
    if not proposal.is_file():
        return "no proposal.md"
    try:
        text = proposal.read_text()
    except OSError as exc:  # unreadable: the change still counts, loudly labelled
        return f"proposal unreadable: {exc}"
    m = _ISSUE_RE.search(text)
    return f"#{m.group(2)}" if m else "no Issue: line"


def main(argv: list[str]) -> int:
    changes_dir = DEFAULT_CHANGES_DIR
    if "--changes-dir" in argv:
        i = argv.index("--changes-dir")
        if i + 1 >= len(argv):
            print("[openspec-backlog] FAIL: --changes-dir needs a path", file=sys.stderr)
            return 2
        changes_dir = Path(argv[i + 1])
    if not changes_dir.is_dir():
        print(f"[openspec-backlog] FAIL: {changes_dir} is not a directory — the OpenSpec "
              f"tree is missing; this check refuses rather than reporting a clean backlog",
              file=sys.stderr)
        return 2

    active = active_changes(changes_dir)
    n = len(active)
    if n < MAX_ACTIVE_OPENSPEC_CHANGES:
        print(f"[openspec-backlog] active={n}/{MAX_ACTIVE_OPENSPEC_CHANGES} — under the cap "
              f"(issue #938): every active change stays validated by openspec-check")
        return 0

    print(f"[openspec-backlog] FAIL: {n} ACTIVE OpenSpec change(s) reached the cap "
          f"{MAX_ACTIVE_OPENSPEC_CHANGES} (issue #938). The backlog must be archived "
          f"before any PR auto-merges to master:")
    for change in active:
        issue = proposal_issue(change)
        print(f"  - {change.name}  (Issue: {issue})")
        print(f"      archive it:  make openspec-archive NAME={change.name}")
        m = re.search(r"#(\d+)", issue)
        if m:
            print(f"      if its PR already merged:  make openspec-record-pr ISSUE={m.group(1)} "
                  f"PR=<pr>  (then archive)")
    print("[openspec-backlog] `openspec-check` stays red — and qa-validate blocks "
          "auto-merge — until the count drops under the cap.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
