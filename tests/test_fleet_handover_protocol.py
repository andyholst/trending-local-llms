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
    "tll-docs",
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
NEXT_DUTY = ("After a delivery, re-read the issue board and claim the oldest unclaimed "
             "actionable issue, or file an evidence-backed issue with a handover to `tll-planner`.")
NEXT_DUTY_ROW = "tests/test_fleet_handover_protocol.py"
#: Issue #1261 — reviewer capacity is the second bottleneck, so the planner's board note
#: must name the PRs already awaiting review and hand them to the reviewer by name.
REVIEWER_BOARD_NOTE = "The board note also names the PRs AWAITING REVIEW"
REVIEWER_HANDOVER = "handover tll-reviewer"
REVIEWER_FIRST = "Spend review capacity BEFORE producing new PRs"
#: Issue #1361 — the ruled `tll-pr-rebase` lane is the repair path for a branch whose
#: conflicts are confined to the generated artifacts, so its habitual-conflict list must
#: name that pair with the regenerate rule; otherwise it stop-and-reports on exactly the
#: PRs it exists to repair.
PR_REBASE_GENERATED = ("OPENSPEC.md", "ARCHITECTURE.md")
PR_REBASE_REGENERATE = ("make openspec-index", "make architecture-refresh")


def test_the_planner_board_note_names_prs_awaiting_review() -> int:
    """Issue #1261: the board note names PRs awaiting review and hands them to tll-reviewer."""
    failed = 0
    skill = ROOT / "agents" / "tll-planner" / "skills" / "tll-planner" / "SKILL.md"
    rel = skill.relative_to(ROOT)
    text = skill.read_text(encoding="utf-8") if skill.is_file() else ""
    for needle, why in (
        (REVIEWER_BOARD_NOTE, "the reviewer-board duty"),
        (REVIEWER_HANDOVER, "the explicit handover to tll-reviewer"),
        (REVIEWER_FIRST, "the spend-review-before-producing order"),
    ):
        if needle in text:
            print(f"ok   {rel} carries {why}")
        else:
            print(f"FAIL {rel} dropped {why}")
            failed += 1
    return failed


def test_next_issue_duty_is_documented() -> int:
    """Issue #1260: a delivery must be followed by a claim or a filed issue."""
    failed = 0
    paths = [ROOT / "AGENTS.md", ROOT / "agents" / "tll-planner" / "skills" / "tll-planner" / "SKILL.md"]
    paths += [ROOT / "agents" / lane / "SOUL.md" for lane in LANES]
    for path in paths:
        rel = path.relative_to(ROOT)
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        if NEXT_DUTY in text:
            print(f"ok   {rel} carries the post-delivery duty")
        else:
            print(f"FAIL {rel} dropped the post-delivery duty")
            failed += 1
    if NEXT_DUTY_ROW not in (ROOT / "AGENTS.md").read_text(encoding="utf-8"):
        print("FAIL AGENTS.md §8 dropped the post-delivery guard row")
        failed += 1
    else:
        print("ok   AGENTS.md §8 names the post-delivery guard row")
    return failed


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


def test_pr_rebase_soul_names_the_generated_artifact_pair() -> int:
    """Issue #1361: the rebase lane's conflict list carries the generated pair."""
    path = ROOT / "agents" / "tll-pr-rebase" / "SOUL.md"
    rel = path.relative_to(ROOT)
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    failed = 0
    for needle, why in (
        (PR_REBASE_GENERATED[0], "OPENSPEC.md in the habitual-conflict list"),
        (PR_REBASE_GENERATED[1], "ARCHITECTURE.md in the habitual-conflict list"),
        (PR_REBASE_REGENERATE[0], "the OPENSPEC.md regenerate command"),
        (PR_REBASE_REGENERATE[1], "the ARCHITECTURE.md regenerate command"),
    ):
        if needle in text:
            print(f"ok   {rel} carries {why}")
        else:
            print(f"FAIL {rel} dropped {why}")
            failed += 1
    return failed


def test_section_8_row_names_the_1361_generated_artifact_guard() -> int:
    """Issue #1363: §8's fleet-handover row must name the #1361 generated-artifact guard."""
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    sec8 = text[text.index("## 8. Regression guards"):]
    rows = [ln for ln in sec8.splitlines() if "tests/test_fleet_handover_protocol.py" in ln]
    failed = 0
    if len(rows) == 1:
        print("ok   AGENTS.md §8 carries exactly one fleet-handover row")
    else:
        print(f"FAIL AGENTS.md §8 fleet-handover row count is {len(rows)}, expected 1")
        failed += 1
    row = rows[0] if rows else ""
    for needle, why in (
        ("test_pr_rebase_soul_names_the_generated_artifact_pair",
         "the #1361 generated-artifact guard name"),
        ("#1361", "issue #1361"),
        ("#1362", "PR #1362"),
    ):
        if needle in row:
            print(f"ok   §8 row names {why}")
        else:
            print(f"FAIL §8 row dropped {why}")
            failed += 1
    if row.startswith("| `") and row.endswith(" |"):
        print("ok   §8 row keeps its two-cell table shape")
    else:
        print("FAIL §8 row lost its two-cell table shape")
        failed += 1
    return failed


STATUS_RULE = "While a test or CI gate runs, post a status comment on the ISSUE"
HOST_STAMP = "user@hostname"


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
            (STATUS_RULE, "the while-you-wait status-comment rule (issue #1232)"),
            (HOST_STAMP, "the user@hostname machine stamp (issue #1232)"),
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
        if STATUS_RULE not in text or HOST_STAMP not in text:
            print(f"FAIL {rel} dropped the status-comment/host-stamp rule (#1232)")
            failed += 1
        else:
            print(f"ok   {rel} carries the status-comment/host-stamp rule (#1232)")
    if failed:
        print(f"FAIL {failed}")
        return 1
    failed += test_rulebook_carries_ghost_run_handoff()
    failed += test_rulebook_carries_ghost_guard_row()
    failed += test_next_issue_duty_is_documented()
    failed += test_the_planner_board_note_names_prs_awaiting_review()
    failed += test_pr_rebase_soul_names_the_generated_artifact_pair()
    failed += test_section_8_row_names_the_1361_generated_artifact_guard()
    if failed:
        print(f"FAIL {failed}")
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
