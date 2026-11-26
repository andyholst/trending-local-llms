#!/usr/bin/env python3
"""The rulebook explicitly allows parallel implementer lanes (issue #1767).

The owner directed (2026-11-26) that up to three `tll-implementer` lanes may work
distinct issues in parallel, each in its own worktree/branch with a signed claim
and a lease-checked push. Before this change §7b/§8 described only a serial
implementer and a one-at-a-time planner, so the three sibling PRs (#1767) each
landed only half the contract. This module pins the §7b bullet and its §8 row
names-only, so a later edit cannot silently drop either half.

It is RED on the base `AGENTS.md` (both the bullet and the row are absent) and
GREEN on this change. Wired into `main()`; `scripts/run_tests.sh` globs it.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "AGENTS.md"
SECTION_7B = "## 7b. TLL fleet"
SECTION_8 = "## 8. Regression guards"
RULE_NEEDLES = (
    "Up to 3 `tll-implementer` lanes may run in parallel (issue #1767)",
    "each on a DISTINCT open issue",
    "its OWN worktree and OWN branch",
    "signed `BOT <lane> · working on #<id> …` claim",
    "lease-checked (`git push --force-with-lease`)",
)
GUARD_ROW = "tests/test_parallel_lane_rulebook.py"
GUARD_NEEDLES = (
    "test_parallel_lane_rulebook",
    "test_parallel_implementer_lanes",
    "test_parallel_planner_dispatch",
)


def _agents() -> str:
    return AGENTS.read_text(encoding="utf-8")


def test_rulebook_section_7b_carries_the_parallel_lane_bullet() -> None:
    text = _agents()
    region = text[text.index(SECTION_7B):text.index(SECTION_8)]
    for needle in RULE_NEEDLES:
        assert needle in region, (
            f"AGENTS.md §7b dropped the parallel-lane rule: {needle!r}"
        )


def test_rulebook_section_8_carries_the_three_guard_needles() -> None:
    text = _agents()
    sec8 = text[text.index(SECTION_8):]
    row = next((ln for ln in sec8.splitlines() if GUARD_ROW in ln), "")
    assert row, "AGENTS.md §8 dropped the parallel-lane guard row"
    for needle in GUARD_NEEDLES:
        assert needle in row, f"the §8 row no longer names {needle!r}"


def test_parallel_lane_rulebook() -> None:
    """The named guard: §7b has the rule AND §8 names all three sibling tests."""
    test_rulebook_section_7b_carries_the_parallel_lane_bullet()
    test_rulebook_section_8_carries_the_three_guard_needles()


def main() -> int:
    failed = 0
    for fn in (
        test_parallel_lane_rulebook,
        test_rulebook_section_7b_carries_the_parallel_lane_bullet,
        test_rulebook_section_8_carries_the_three_guard_needles,
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
