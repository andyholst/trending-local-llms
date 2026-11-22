#!/usr/bin/env python3
"""Every tll lane's SOUL.md + the planner skill carry the handover protocol (issue #1189).

The fleet's lanes claim work with a signed `working on` comment (issue #703), but
nothing made a lane HAND OVER: a lane finished and the thread stopped at "working
on", so the planner and the owner had to re-read every thread to learn who owned
the next step. Issue #1189 makes the handover comment shape explicit in every
lane's SOUL.md and in the planner skill. This module locks that shape, so a later
edit cannot silently drop it from one lane.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANES = (
    "tll-planner",
    "tll-architect",
    "tll-security",
    "tll-reviewer",
    "tll-implementer",
    "tll-tester",
    "tll-pr-rebase",
)
HANDOVER_SHAPE = "· done #<id> · handover <next-lane|owner|none>"
PROGRESS_RULE = "Progress comments are the record"
REMIT_RULE = "Never work outside your remit"
MULTI_MACHINE = "The fleet spans several machines."
RACE_GUARD = "Claim twice before you start (race guard)."
PLANNER_DISPATCH = "· dispatch #<id> · lane <lane> · base <sha>"
GHOST_RULE = "A 0-job `action_required` head is a never-started run, not a red gate"
GHOST_OWN_BRANCH = "re-push ONLY its own branch with an owner-git-identity empty commit"
GHOST_VERIFY = "verify with `gh run view <id> --json jobs` that the new run has jobs"
GHOST_GUARD_ROW = "tests/test_fleet_handover_protocol.py"


def test_rulebook_carries_ghost_run_handoff() -> int:
    """The #1251 rulebook bullet survives: recognise, report, own-branch, verify."""
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    failed = 0
    for needle, why in (
        (GHOST_RULE, "the never-started-run rule"),
        (GHOST_OWN_BRANCH, "the own-branch-only recovery"),
        (GHOST_VERIFY, "the jobs-exist verification"),
    ):
        if needle in text:
            print(f"ok   AGENTS.md carries {why}")
        else:
            print(f"FAIL AGENTS.md dropped {why}")
            failed += 1
    return failed


def test_rulebook_carries_ghost_guard_row() -> int:
    """§8 names the module that locks the ghost-run behavior."""
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    if GHOST_GUARD_ROW + "`" not in text and GHOST_GUARD_ROW not in text:
        print(f"FAIL AGENTS.md §8 dropped the {GHOST_GUARD_ROW} guard row")
        return 1
    print("ok   AGENTS.md names the ghost-run guard module")
    return 0


def main() -> int:
    failed = 0
    for lane in LANES:
        path = ROOT / "agents" / lane / "SOUL.md"
        rel = path.relative_to(ROOT)
        if not path.is_file():
            print(f"FAIL {rel} missing")
            failed += 1
            continue
        text = path.read_text(encoding="utf-8")
        for needle, why in (
            (HANDOVER_SHAPE, "the signed handover comment shape"),
            (PROGRESS_RULE, "the progress-comment rule"),
            (MULTI_MACHINE, "the multi-machine shared-board rule"),
            (RACE_GUARD, "the double-claim race guard"),
            (REMIT_RULE, "the remit handover rule"),
        ):
            if needle not in text:
                print(f"FAIL {rel} dropped {why}")
                failed += 1
            else:
                print(f"ok   {rel} carries {why}")
    skill = ROOT / "agents" / "tll-planner" / "skills" / "tll-planner" / "SKILL.md"
    rel = skill.relative_to(ROOT)
    if not skill.is_file():
        print(f"FAIL {rel} missing")
        failed += 1
    else:
        text = skill.read_text(encoding="utf-8")
        if PLANNER_DISPATCH not in text:
            print(f"FAIL {rel} dropped the dispatch/handover shape")
            failed += 1
        else:
            print(f"ok   {rel} carries the dispatch/handover shape")
        if "parent fleet issue #682 is closed" not in text:
            print(f"FAIL {rel} does not state the standing board rule (#682 closed)")
            failed += 1
        else:
            print(f"ok   {rel} states the standing board rule (#682 closed)")
    if failed:
        print(f"FAIL {failed}")
        return 1
    failed += test_rulebook_carries_ghost_run_handoff()
    failed += test_rulebook_carries_ghost_guard_row()
    if failed:
        print(f"FAIL {failed}")
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
