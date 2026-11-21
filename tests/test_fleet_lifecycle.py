#!/usr/bin/env python3
"""The tll lifecycle lives on the ISSUE thread and a host must match fetched master (issue #1209).

Every lane comments on the issue BEFORE it works; the planner reads those comments to
delegate; an implementer's PR hands over to the reviewer on the issue, not on the PR.
This module locks those shapes AND drives the real host-sync seam over a scratch home:
green on a synced tree, red on a planted byte-loss or a bad base. No stand-in for the
system under test -- the guard itself is executed.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEAM = ROOT / "scripts" / "fleet_host_sync_check.py"
LANES = (
    "tll-planner",
    "tll-architect",
    "tll-security",
    "tll-reviewer",
    "tll-implementer",
    "tll-tester",
    "tll-pr-rebase",
)
BEFORE = "Comment on the issue BEFORE you do the work."
PR_SHAPE = "· pr #<id> · PR #<n> · base <sha> · handover tll-reviewer"
REVIEW_SHAPE = "· reviewing #<id> · PR #<n>"
PLANNER_READS = "The planner reads the issue comments to delegate accordingly."
AGENTS_SECTION = "TLL fleet — lifecycle, delegation and divergence gate"
FOLLOW_UP = "Always follow up on the issue"


def check(cond: bool, msg: str) -> int:
    if cond:
        print(f"ok   {msg}")
        return 0
    print(f"FAIL {msg}")
    return 1


def run_seam(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SEAM), *argv],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def scratch_home(dest: Path) -> None:
    for lane in LANES:
        src = ROOT / "agents" / lane
        (dest / lane / "skills" / lane).mkdir(parents=True)
        shutil.copyfile(src / "SOUL.md", dest / lane / "SOUL.md")
        shutil.copyfile(src / "config.yaml", dest / lane / "config.yaml")
        shutil.copyfile(
            src / "skills" / lane / "SKILL.md",
            dest / lane / "skills" / lane / "SKILL.md",
        )


def test_every_lane_carries_the_pr_handover_shapes() -> int:
    failed = 0
    for lane in LANES:
        path = ROOT / "agents" / lane / "SOUL.md"
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        for needle, why in (
            (BEFORE, "comment-before-work"),
            (PR_SHAPE, "the PR-to-reviewer issue comment"),
            (REVIEW_SHAPE, "the reviewer's issue comment"),
            (PLANNER_READS, "the planner reads comments to delegate"),
            (FOLLOW_UP, "always follow up on the issue"),
        ):
            failed += check(needle in text, f"{lane}/SOUL.md carries {why}")
    return failed


def test_planner_skill_reads_the_comments() -> int:
    skill = ROOT / "agents" / "tll-planner" / "skills" / "tll-planner" / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    failed = check(BEFORE in text, "planner skill: comment before work")
    for needle, why in (
        ("Read before you dispatch.", "planner re-reads the thread"),
        ("answering <comment-id>", "dispatch names the comment it answers"),
        ("A PR is never the handover.", "PR is not the handover"),
        ("Always follow up on the issue.", "follow-up rule"),
    ):
        failed += check(needle in text, f"planner skill carries {why}")
    return failed


def test_reviewer_shapes_are_in_the_rulebook() -> int:
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    failed = check(AGENTS_SECTION in text, "AGENTS.md carries the tll fleet section")
    for needle, why in (
        (BEFORE, "comment-before-work"),
        (PR_SHAPE, "PR-to-reviewer shape"),
        (REVIEW_SHAPE, "reviewer shape"),
        (PLANNER_READS, "planner reads comments"),
        ("fleet-host-sync-check", "the host divergence gate"),
        ("tests/test_fleet_lifecycle.py", "the §8 guard row"),
    ):
        failed += check(needle in text, f"AGENTS.md carries {why}")
    return failed


def test_real_seam_accepts_a_synced_home() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / "profiles"
        home.mkdir()
        scratch_home(home)
        got = run_seam("--base", "HEAD", "--root", str(ROOT), "--profiles-home", str(home))
        ok = check(got.returncode == 0, "real seam accepts a home synced at HEAD")
        print("      " + (got.stdout or got.stderr).strip().splitlines()[-1])
        return ok


def test_real_seam_refuses_a_diverged_soul() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / "profiles"
        home.mkdir()
        scratch_home(home)
        victim = home / "tll-tester" / "SOUL.md"
        victim.write_bytes(victim.read_bytes()[:-1])  # one byte short
        got = run_seam("--base", "HEAD", "--root", str(ROOT), "--profiles-home", str(home))
        failed = check(got.returncode == 1, "a one-byte drift is refused")
        failed += check(
            "tll-tester/SOUL.md" in got.stdout and "diverges from" in got.stdout,
            "the refusal names the lane and the file",
        )
        return failed


def test_real_seam_refuses_a_bad_base() -> int:
    got = run_seam("--base", "no-such-ref-1209", "--root", str(ROOT))
    failed = check(got.returncode == 2, "an unresolvable base exits 2 (undecidable)")
    failed += check("REFUSED" in got.stdout, "the refusal is loud, not a silent clean")
    return failed


def test_ci_wires_the_guard_on_pr_and_push() -> int:
    workflow = (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text(encoding="utf-8")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    failed = check("pull_request:" in workflow, "qa-validate has a pull_request trigger")
    failed += check("\n  push:" in workflow, "qa-validate has a push trigger")
    failed += check("run: make test" in workflow, "qa-validate runs make test")
    failed += check(
        "run: make fleet-host-sync-check" in workflow,
        "qa-validate calls make fleet-host-sync-check",
    )
    failed += check(
        "fleet_host_sync_check.py" not in workflow,
        "no workflow reaches the script past the Makefile (rule 6m)",
    )
    failed += check("_fleet-host-sync-check:" in makefile, "Makefile defines the internal recipe")
    failed += check("fleet-host-sync-check: ##" in makefile, "Makefile defines the public target")
    runner = subprocess.run(
        ["bash", str(ROOT / "scripts" / "run_tests.sh"), "--list"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    failed += check(
        "test_fleet_lifecycle.py" in runner.stdout,
        "the ONE runner discovers this module (make test)",
    )
    return failed


def main() -> int:
    failed = 0
    for fn in (
        test_every_lane_carries_the_pr_handover_shapes,
        test_planner_skill_reads_the_comments,
        test_reviewer_shapes_are_in_the_rulebook,
        test_real_seam_accepts_a_synced_home,
        test_real_seam_refuses_a_diverged_soul,
        test_real_seam_refuses_a_bad_base,
        test_ci_wires_the_guard_on_pr_and_push,
    ):
        failed += fn()
    if failed:
        print(f"FAIL {failed}")
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
