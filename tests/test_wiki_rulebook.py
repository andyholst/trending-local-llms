#!/usr/bin/env python3
"""Pin the rulebook half of the architect's wiki-freshness duty (issue #1773).

The owner directed that `tll-architect` owns documentation freshness — a DAILY CI
check and a WEEKLY host cron, updating false claims, archiving obsolete pages with
a dated marker, filing an evidence-backed issue per change, never inventing a
value and never hand-editing a generated artifact. The duty and its regression
guard row must live in `AGENTS.md` §7b/§8 (rule 3c), not only in a role mirror or a
chat note. This module pins those needles at SOURCE level: deleting the §7b
bullet, the §8 row, the rule-3c declaration clause, or any existing §7b rule
turns `make test` red.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "AGENTS.md"
SECTION_7B = "## 7b. TLL fleet"
SECTION_8 = "## 8. Regression guards"
RULE_3C_NOTE = "Rule 3c note:"
GUARD_MODULE = "tests/test_wiki_rulebook.py"

#: The §7b duty, named explicitly so a rewording that drops a clause is refused.
ARCHITECT_DUTY_NEEDLES = (
    "tll-architect",
    "wiki/documentation freshness",
    "DAILY CI check",
    "weekly host cron",
    "UPDATE a document whose statement is false",
    "ARCHIVE a document whose subject is obsolete",
    "docs/archive/",
    "dated marker",
    "FILE one `enhancement` issue",
    "measured evidence",
    "Never invent a value",
    "never rewrite a generated artifact",
    "ONE scheduled pipeline",
)

#: The §8 row must name this module and all three guard functions, plus the seam.
ROW_NEEDLES = (
    GUARD_MODULE,
    "test_architect_wiki_role",
    "test_wiki_maintenance",
    "test_wiki_rulebook",
    "#1773",
    "wiki-maintenance",
)

#: The new duty is ADDITIVE: none of these pre-existing §7b rules may disappear.
EXISTING_RULE_NEEDLES = (
    "Comment on the issue BEFORE you do the work",
    "The planner runs `make dispatch-check`",
    "Fetched-base sync is mandatory",
    "Lanes change locally and PUSH; CI verifies",
)


def _agents() -> str:
    return AGENTS.read_text(encoding="utf-8")


def _region(text: str, start: str, end: str | None) -> str:
    begin = text.index(start)
    return text[begin:text.index(end, begin)] if end else text[begin:]


def _row(text: str) -> str:
    sec8 = _region(text, SECTION_8, None)
    return next((ln for ln in sec8.splitlines() if GUARD_MODULE in ln), "")


def test_architect_wiki_role() -> None:
    """§7b declares the architect's daily-CI / weekly-cron wiki-maintenance duty."""
    region = _region(_agents(), SECTION_7B, SECTION_8)
    for needle in ARCHITECT_DUTY_NEEDLES:
        assert needle in region, (
            f"AGENTS.md §7b dropped the architect wiki-duty needle: {needle!r}")


def test_wiki_maintenance() -> None:
    """§8 carries a row naming this module and all three guard functions."""
    row = _row(_agents())
    assert row, "AGENTS.md §8 dropped the wiki-rulebook guard row"
    for needle in ROW_NEEDLES:
        assert needle in row, f"the §8 wiki-rulebook row no longer names {needle!r}"


def test_wiki_rulebook() -> None:
    """The rule-3c clause, both edits and every existing §7b rule survive."""
    text = _agents()
    note = next((ln for ln in text.splitlines() if RULE_3C_NOTE in ln), "")
    assert "issue #1773" in note, (
        "AGENTS.md §7b 'Rule 3c note' carries no #1773 declaration clause")
    region = _region(text, SECTION_7B, SECTION_8)
    assert "wiki/documentation freshness" in region, (
        "AGENTS.md §7b carries no architect wiki-freshness bullet")
    assert "test_architect_wiki_role" in _region(text, SECTION_8, None), (
        "AGENTS.md §8 does not name the wiki-rulebook guard functions")
    for needle in EXISTING_RULE_NEEDLES:
        assert needle in region, f"an existing §7b rule was dropped: {needle!r}"


def main() -> int:
    failed = 0
    for fn in (test_architect_wiki_role, test_wiki_maintenance, test_wiki_rulebook):
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
