#!/usr/bin/env python3
"""A tracker sweep may not close a diagnosed failure without a landed fix (issue #1256).

The 04:27 sweep closed #827/#828 on four later green issue-bot runs. The
pipeline-failure guard correctly reds a CLOSED row with no fix PR and no guard
test, so that one hygiene act blocked every open PR's validate. This module
pins the rulebook rule that prevents a repeat.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULE_NEEDLES = (
    "A tracker sweep may close a `pipeline-run-failure` issue only when its ledger row names a merged fix PR and a collected guard test",
    "Later green runs alone are NOT a landed fix",
)
GUARD_ROW = "tests/test_tracker_sweep_closure_guard.py"


def test_rulebook_carries_sweep_closure_guard() -> None:
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for needle in RULE_NEEDLES:
        assert needle in text, f"AGENTS.md dropped the sweep-closure rule: {needle}"


def test_rulebook_carries_guard_row() -> None:
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert GUARD_ROW in text, "AGENTS.md §8 dropped the tracker-sweep guard row"


def main() -> int:
    failed = 0
    for fn in (test_rulebook_carries_sweep_closure_guard, test_rulebook_carries_guard_row):
        try:
            fn()
        except AssertionError as exc:
            print(f"FAIL {fn.__name__}: {exc}")
            failed += 1
        else:
            print(f"ok   {fn.__name__}")
    if failed:
        print(f"FAIL {failed}")
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
