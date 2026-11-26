#!/usr/bin/env python3
"""Issue #1767: the implementer lane mirrors must declare the CONCURRENT-lane contract.

The guard reads the REAL tracked `agents/tll-implementer/SOUL.md` and skill, not a
fixture. It fails when any of the seven lane obligations is missing, and it proves
RED by removing the added contract section from each head text and re-running the
same checker: the pre-contract text must fail. Wired into its own main() so the
repo's `test_unit_tests_really_run` wiring guard sees it.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOUL_REL = "agents/tll-implementer/SOUL.md"
SKILL_REL = "agents/tll-implementer/skills/tll-implementer/SKILL.md"
HEADING = "## Concurrent-lane contract (issue #1767)"

# (label, needle) — every needle is an obligation the owner named in #1767.
# The first seven are the bullet contracts; the rest are the operational clauses
# that stop a heading-only edit from passing the guard.
OBLIGATIONS = (
    ("one issue + one worktree + one branch per lane",
     "**One issue, one worktree, one branch per lane.**"),
    ("no shared issue, branch or file edits",
     "Two lanes never work the same issue, share a branch, or edit the same file."),
    ("signed claim on the issue thread before work",
     "**Signed claim before work.**"),
    ("claim is posted on the issue's own thread",
     "on the issue's OWN thread before starting"),
    ("no shared branch/file edits across lanes",
     "**No shared branch or file edits.**"),
    ("overlap is handed to the planner",
     "Overlapping file claims mean stop and hand over to `tll-planner`."),
    ("max 3 live implementer lanes",
     "**At most 3 live implementer lanes.**"),
    ("three lanes, distinct issues and file sets",
     "Up to three lanes run concurrently, each on a distinct issue and a distinct file set;"),
    ("lease-checked push",
     "**Lease-checked push.**"),
    ("push uses --force-with-lease",
     "Push with `--force-with-lease` against the sha you last read from `origin/<branch>`;"),
    ("no master push, no merge",
     "**No master push, no merge.**"),
    ("no master push / gh pr merge / self-approval",
     "Never push to `master`, never run `gh pr merge`, never approve your own pull request;"),
    ("each lane loads its own SOUL.md and SKILL.md",
     "**Every lane loads its own SOUL.md and SKILL.md.**"),
    ("own profile soul and skill are read before claiming",
     "reads its own profile's `SOUL.md` and skill `SKILL.md`"),
)

_PASS = 0
_FAIL = 0


def check(name: str, cond: bool, detail: object = "") -> int:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
        return 0
    _FAIL += 1
    print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))
    return 1


def missing(text: str) -> list[str]:
    """Every declared lane obligation the given SOUL/SKILL text fails to carry."""
    absent: list[str] = []
    if HEADING not in text:
        absent.append(HEADING)
    for label, needle in OBLIGATIONS:
        if needle not in text:
            absent.append(label)
    return absent


def pre_contract_text(text: str) -> str:
    """The same file with ONLY the added `#1767` section removed.

    This is the base text byte-for-byte: the change adds one contiguous section
    and changes no other line, so cutting that section reconstructs the revision
    the guard must fail on. It stays valid after the change reaches master,
    unlike reading a moving `origin/master` ref.
    """
    if HEADING not in text:
        return text  # base text: no added section to cut; no crash, just RED below
    start = text.index(HEADING)
    end = text.index("\n## ", start + len(HEADING))
    return text[:start] + text[end + 1:]


def test_soul_declares_the_concurrent_lane_contract() -> int:
    text = (ROOT / SOUL_REL).read_text(encoding="utf-8")
    return check("SOUL.md declares every concurrent-lane obligation",
                 not missing(text), missing(text))


def test_skill_declares_the_concurrent_lane_contract() -> int:
    text = (ROOT / SKILL_REL).read_text(encoding="utf-8")
    return check("SKILL.md declares every concurrent-lane obligation",
                 not missing(text), missing(text))


def test_the_guard_is_red_on_the_pre_contract_text() -> int:
    failed = 0
    for rel in (SOUL_REL, SKILL_REL):
        text = (ROOT / rel).read_text(encoding="utf-8")
        base = pre_contract_text(text)
        failed += check(f"{rel}: head passes the guard", not missing(text), missing(text))
        failed += check(f"{rel}: pre-contract text FAILS the guard",
                        bool(missing(base)), "guard passed on the base text — dead test")
        failed += check(f"{rel}: only the new section was removed",
                        text != base and HEADING not in base, "")
    return failed


def test_a_heading_only_edit_cannot_satisfy_the_guard() -> int:
    """A contract section with just the title must stay RED on the obligations."""
    partial = "# TLL Implementer\n\n" + HEADING + "\n\nParallel lanes are nice.\n"
    failed = check("heading alone is refused", bool(missing(partial)), missing(partial))
    failed += check("the refusal lists real obligations, not just the heading",
                    len(missing(partial)) > 1, missing(partial))
    return failed


def main() -> int:
    for fn in (
        test_soul_declares_the_concurrent_lane_contract,
        test_skill_declares_the_concurrent_lane_contract,
        test_the_guard_is_red_on_the_pre_contract_text,
        test_a_heading_only_edit_cannot_satisfy_the_guard,
    ):
        fn()
    if _FAIL:
        print(f"FAIL {_FAIL}")
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
