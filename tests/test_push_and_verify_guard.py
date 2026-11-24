#!/usr/bin/env python3
"""A tll lane changes locally and PUSHES; qa-validate verifies (issues #1423/#1589).

#1423 landed push-and-verify in the two lane skill mirrors and explicitly left the
rulebook half to rule 3c. This module pins the §7b bullet and its §8 row names-only,
so deleting either turns `make test` red.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "AGENTS.md"
SECTION_7B = "## 7b. TLL fleet"
SECTION_8 = "## 8. Regression guards"
RULE_NEEDLES = (
    "Lanes change locally and PUSH; CI verifies",
    "run ONLY the fast offline checks",
    "confirm CI registered on the new head",
    "are CI-ONLY",
)
GUARD_ROW = "tests/test_push_and_verify_guard.py"


def _agents() -> str:
    return AGENTS.read_text(encoding="utf-8")


def test_rulebook_section_7b_carries_the_push_and_verify_bullet() -> None:
    text = _agents()
    region = text[text.index(SECTION_7B):text.index(SECTION_8)]
    for needle in RULE_NEEDLES:
        assert needle in region, f"AGENTS.md §7b dropped the push-and-verify rule: {needle!r}"


def test_rulebook_section_8_carries_the_guard_row() -> None:
    text = _agents()
    sec8 = text[text.index(SECTION_8):]
    row = next((ln for ln in sec8.splitlines() if GUARD_ROW in ln), "")
    assert row, "AGENTS.md §8 dropped the push-and-verify guard row"
    for needle in ("`make validate`", "`make test`", "`make live-smoke`"):
        assert needle in row, f"the §8 row no longer names {needle} CI-only"


def main() -> int:
    failed = 0
    for fn in (
        test_rulebook_section_7b_carries_the_push_and_verify_bullet,
        test_rulebook_section_8_carries_the_guard_row,
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
