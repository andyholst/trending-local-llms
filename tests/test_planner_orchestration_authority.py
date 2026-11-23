#!/usr/bin/env python3
"""The planner skill carries the owner's 2026-11-23 orchestration/delegation authority (issue #1398).

The owner directed on 2026-11-23 that `tll-planner` has FULL authority to orchestrate and delegate: it
STARTS the other lanes itself instead of waiting for the owner on the host. That authority lived only in
this host's session context, and a fleet-sync on `da86387c` reverted the host-only edit — so the
behaviour must live in the reviewed tree, in the planner's skill.

`agents/tll-planner/SOUL.md` is a protected agent-instruction file (`security.protected_instruction_files`
is `true`), so a headless leg cannot write it (rule 3c); the skill is this change's home and the guard
reads THAT file. Every assertion below reads the REAL skill from the repository — no fixture, no copy,
no mock (rule 6m). Deleting the section, a guardrail or a pitfall from the skill reds this module.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "agents" / "tll-planner" / "skills" / "tll-planner" / "SKILL.md"
RUNNER = ROOT / "scripts" / "run_tests.sh"

_PASS = 0
_FAIL = 0


def check(name: str, cond: bool, detail: object = "") -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


#: The section this change adds. Each needle is one clause of the owner's directive or one guardrail.
SECTION_HEADING = "### Starting a lane (owner directive 2026-11-23)"
MECHANISM = "env -u HERMES_HOME -u HERMES_SESSION_PROFILE hermes -p <lane> chat"
BACKGROUND = "terminal(background=true)"
MONITOR = "process_manage"
SIGNED_DISPATCH = "Delegation is still by a signed dispatch COMMENT on the issue thread"
NO_TREE_WRITE = "NEVER writes the tree"
NO_MERGE = "NEVER merges"
NO_CRON = "No cron and no Actions schedule"
YOLO = "--yolo --accept-hooks"
APPROVALS = "approvals.single_query_mode: deny"
OWNER_CHECKOUT = "check the owner's checkout with `git status`"
LANE_DURATION = "30–70 min"


def _skill_text() -> str:
    return SKILL.read_text(encoding="utf-8")


def test_the_planner_skill_records_the_orchestration_authority() -> None:
    """The directive AND its mechanism are written down in the planner skill."""
    text = _skill_text()
    check("skill: the owner directive section exists", SECTION_HEADING in text, SECTION_HEADING)
    check("skill: the directive names the owner and the date",
          "The owner directed on 2026-11-23 that this lane has **full authority to orchestrate and delegate**"
          in text, "the directive sentence")
    for needle, why in (
        (MECHANISM, "the exact start-a-lane command"),
        ("--query-file <file> --oneshot", "the query-file + oneshot flags"),
        (BACKGROUND, "the background launch"),
        (MONITOR, "the monitor tool"),
    ):
        check(f"skill: names {why}", needle in text, needle)
    if SECTION_HEADING not in text:
        check("skill: the mechanism sits in the directive's own section", False,
              "the section heading is absent — nothing to scope")
        return
    section = text.split(SECTION_HEADING, 1)[1].split("\n## ", 1)[0]
    check("skill: the mechanism sits in the directive's own section",
          MECHANISM in section and BACKGROUND in section and MONITOR in section, section[:200])


def test_the_guardrails_survive_beside_the_authority() -> None:
    """The authority is bounded: signed comment, no tree write, no merge, no cron."""
    text = _skill_text()
    if SECTION_HEADING not in text:
        check("skill: carries the guardrails", False, "the directive section is absent")
        return
    section = text.split(SECTION_HEADING, 1)[1].split("\n## ", 1)[0]
    for needle, why in (
        (SIGNED_DISPATCH, "delegation stays a signed dispatch comment"),
        (NO_TREE_WRITE, "the planner never writes the tree"),
        (NO_MERGE, "the planner never merges"),
        (NO_CRON, "no cron and no Actions schedule"),
    ):
        check(f"skill: carries {why}", needle in section, needle)


def test_the_pitfalls_are_recorded() -> None:
    """A lane that starts another lane hits these; the skill names each."""
    text = _skill_text()
    if SECTION_HEADING not in text:
        check("skill: names the pitfalls", False, "the directive section is absent")
        return
    section = text.split(SECTION_HEADING, 1)[1].split("\n## ", 1)[0]
    for needle, why in (
        (YOLO, "the --yolo --accept-hooks flag set"),
        (APPROVALS, "the approval mode it clears"),
        (OWNER_CHECKOUT, "the owner-checkout check after a lane run"),
        (LANE_DURATION, "the 30–70 min lane duration"),
    ):
        check(f"skill: names {why}", needle in section, needle)


def test_the_guard_is_discovered_by_the_one_runner() -> None:
    """The module is one the ONE runner lists, so `make test` executes it (issues #176/#192/#890)."""
    proc = subprocess.run(
        ["bash", str(RUNNER), "--list"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    listed = [Path(line).name for line in proc.stdout.splitlines() if line.strip()]
    check("runner: --list exits 0", proc.returncode == 0, proc.stderr[:300])
    check("runner: this module is listed", Path(__file__).name in listed,
          f"missing from {len(listed)} listed modules")
    # The CI hygiene rule: a `test_*` that `main()` never calls is dead code that never runs.
    import ast

    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    defs = [n.name for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
    main = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main"), None)
    check("guard: the module has a main() runner", main is not None)
    if main is None:
        return
    used = {n.id for n in ast.walk(main) if isinstance(n, ast.Name)}
    uncalled = [d for d in defs if d not in used]
    check("guard: every test_* is called from main()", not uncalled, uncalled)
    check("guard: the module exits non-zero on failure",
          "sys.exit(main())" in Path(__file__).read_text(encoding="utf-8"), "")


def main() -> int:
    print("planner orchestration authority (issue #1398)")
    for fn in (
        test_the_planner_skill_records_the_orchestration_authority,
        test_the_guardrails_survive_beside_the_authority,
        test_the_pitfalls_are_recorded,
        test_the_guard_is_discovered_by_the_one_runner,
    ):
        print(f"-- {fn.__name__}")
        fn()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
