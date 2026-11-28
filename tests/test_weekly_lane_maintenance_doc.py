#!/usr/bin/env python3
"""Guard the weekly lane-maintenance checklist (issue #1834).

The doc is the deliverable, so the guards read the REAL doc and fail when a stated
obligation is removed. They do not mock the file under test. The collaboration-doc
link guard is conditional: that doc arrives with companion PR #1836, so it is checked
only when the file is present on the tree being tested.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "weekly-lane-maintenance.md"
COLLAB = ROOT / "docs" / "fleet-collaboration.md"

#: Module-level failure counter (house shape, issue #1301): the pytest parity plugin
#: reads this after collecting the module, so a bare pytest run cannot hide a failed guard.
_FAIL = 0


def check(condition: bool, message: str) -> int:
    global _FAIL
    if not condition:
        print(f"FAIL {message}")
        _FAIL += 1
        return 1
    return 0


def doc_text() -> str:
    return DOC.read_text(encoding="utf-8") if DOC.is_file() else ""


def test_the_pass_is_a_cadence_not_a_timer() -> int:
    """The owner starts a weekly cadence; no cron and no new Actions schedule."""
    text = doc_text()
    needles = (
        "# Weekly lane-maintenance pass",
        "cadence, not a timer",
        "hermes -p tll-planner chat",
        "**No Hermes cron**",
        "**no new GitHub Actions `schedule:`**",
        "Do not add a workflow that runs",
        "do not edit an existing schedule",
        "The only scheduled pipeline in the tree is the data gatherer",
    )
    failed = 0
    for needle in needles:
        failed += check(needle in text, f"maintenance doc states {needle!r}")
    return failed


def test_the_pass_names_the_exact_per_host_sync_command() -> int:
    """The per-host step carries the exact command and the files it compares."""
    text = doc_text()
    needles = (
        "git fetch origin master",
        "make fleet-host-sync-check BASE=origin/master",
        "From THIS host",
        "freshly fetched repo",
        "`SOUL.md`",
        "`skills/<lane>/SKILL.md`",
        "agents/tll-*/SOUL.md",
        "`AGENTS.md`",
    )
    failed = 0
    for needle in needles:
        failed += check(needle in text, f"per-host sync step names {needle!r}")
    return failed


def test_the_pass_defines_the_drift_filing_path() -> int:
    """Drift is filed and fixed through the write lane, never force-greened."""
    text = doc_text()
    needles = (
        "small `enhancement` issue",
        "`tll-implementer`",
        "#696",
        "**Never wipe Hermes runtime stamps",
        "byte-copy a host-ahead note",
    )
    failed = 0
    for needle in needles:
        failed += check(needle in text, f"drift-filing path states {needle!r}")
    return failed


def test_the_pass_covers_roster_collab_board_and_record() -> int:
    """Steps 2-5 of issue #1834 are all present, including the signed record."""
    text = doc_text()
    needles = (
        "<lane>-2",
        "<lane>-3",
        "<lane>-4",
        "one `tll-planner` on each",
        "hermes -p <name> doctor",
        "docs/fleet-collaboration.md",
        "in-progress lanes",
        "PRs awaiting review",
        "base sha",
        "drift found",
        "issues filed",
        "next pass",
    )
    failed = 0
    for needle in needles:
        failed += check(needle in text, f"maintenance doc covers {needle!r}")
    failed += check(text.count("- [ ]") >= 5, "the doc carries a runnable five-step checklist")
    return failed


def test_the_collaboration_doc_points_at_this_checklist() -> int:
    """Once PR #1836 lands, §6 of the canonical doc links to this checklist."""
    if not COLLAB.is_file():
        return 0  # companion doc not on this base yet — checked after it merges
    text = COLLAB.read_text(encoding="utf-8")
    return check(
        "weekly-lane-maintenance.md" in text,
        "collaboration doc cross-links the weekly maintenance checklist",
    )


def main() -> int:
    global _FAIL
    _FAIL = 0
    failed = 0
    for fn in (
        test_the_pass_is_a_cadence_not_a_timer,
        test_the_pass_names_the_exact_per_host_sync_command,
        test_the_pass_defines_the_drift_filing_path,
        test_the_pass_covers_roster_collab_board_and_record,
        test_the_collaboration_doc_points_at_this_checklist,
    ):
        failed += fn()
    if failed:
        print(f"FAIL {failed}")
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
