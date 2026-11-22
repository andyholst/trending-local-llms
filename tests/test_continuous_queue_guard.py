#!/usr/bin/env python3
"""A tll lane never stops after one delivery (issue #1258).

The board review on 2026-11-22 showed 14 open issues already carrying a PR and
24 with none. This guard pins the rulebook rule that turns "keep working" into
a parseable lifecycle duty rather than an ad-hoc habit.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEEDLES = (
    "After a delivery, re-read the issue board and claim the oldest unclaimed actionable issue, or file an evidence-backed issue with a handover to `tll-planner`.",
    "A `done`/`handover` comment followed by silence is not a delivery",
)
GUARD_ROW = "tests/test_continuous_queue_guard.py"


def test_rulebook_carries_continuous_queue_rule() -> None:
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert NEEDLES[0] in text, "AGENTS.md dropped the continuous-queue rule"


def test_rulebook_carries_innovation_rule() -> None:
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert NEEDLES[1] in text, "AGENTS.md dropped the innovation-from-vision rule"


def test_rulebook_carries_guard_row() -> None:
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert GUARD_ROW in text, "AGENTS.md §8 dropped the continuous-queue guard row"


def main() -> int:
    failed = 0
    for fn in (
        test_rulebook_carries_continuous_queue_rule,
        test_rulebook_carries_innovation_rule,
        test_rulebook_carries_guard_row,
    ):
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
