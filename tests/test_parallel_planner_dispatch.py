#!/usr/bin/env python3
"""RED-first source guard for the planner's parallel implementer dispatch (issue #1767).

The owner directed (2026-11-26) that the board is not drained one issue at a time:
up to 3 `tll-implementer` lanes may run concurrently against DISTINCT open issues,
each with its own query file, signed claim, worktree and lease-checked branch, and
one board-visible bookend pair. The rule lives in the planner's skill — the
operational prompt that starts lanes. `agents/tll-planner/SOUL.md` is a rule-3c
protected instruction file, so this headless change declares that mirror as owed in
`findings/1767-planner.md` instead of forcing a protected write.

Every assertion reads the REAL files: the fetched base blob through `git show` and
the checked-out skill from disk. No fixtures, no stand-ins, no mocks (rule 6m).
On the fetched base the contract is absent (RED); on the fixed head it is present
(GREEN). A `test_*` that `main()` never calls is dead code in `make test` (issue
#890/#176), so this module guards its own wiring too.

Run:  python3 tests/test_parallel_planner_dispatch.py   or   make test
"""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_REL = "agents/tll-planner/skills/tll-planner/SKILL.md"
SKILL = ROOT / SKILL_REL
RUNNER = ROOT / "scripts" / "run_tests.sh"

#: The base this change was cut from (fetched `origin/master` before branching).
BASE_SHA = "37c6d88150fdb73fd0583a59099aee0b418d7927"

#: One clause per owner requirement. Each is a literal fragment of the landed
#: skill text; none of them occurs in the fetched base (the RED half of the test).
CONTRACT: tuple[tuple[str, str], ...] = (
    ("up to 3 implementer lanes CONCURRENTLY", "the concurrent lane ceiling"),
    ("DISTINCT open issues", "one issue per lane"),
    ("one query file per lane", "per-lane dispatch prompt"),
    ("one signed issue claim per lane", "per-lane signed claim / race guard"),
    ("one worktree per lane", "tree isolation per lane"),
    ("one lease-checked branch per lane", "force-with-lease branch pin"),
    ("one board-visible bookend per lane", "start + done comment on the thread"),
    ("a tech-debt issue or a protected-rulebook issue", "no dispatch onto protected work"),
    ("owner sign-off", "the human gate for rule-3c / tech-debt"),
    ("no merge and no push to master", "qa-validate alone merges green heads"),
)
SECTION = "### Parallel implementer dispatch (owner directive, issue #1767)"


def _base_skill() -> str:
    """The real base blob, read with git — never the owner's checkout."""
    proc = subprocess.run(
        ["git", "show", f"{BASE_SHA}:{SKILL_REL}"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"cannot read the fetched base skill at {BASE_SHA}:{SKILL_REL}: "
            f"{proc.stderr.strip()[:300]} — a guard that cannot read the base "
            f"is loud, never a silent green"
        )
    return proc.stdout


def _missing(text: str) -> list[str]:
    """The contract clauses absent from *text*."""
    return [why for needle, why in CONTRACT if needle not in text]


def test_the_guard_is_red_on_the_fetched_base() -> None:
    """The base really lacks every clause: this is a RED-first change."""
    base = _base_skill()
    absent = [why for needle, why in CONTRACT if needle not in base]
    assert absent == [why for _, why in CONTRACT], (
        f"the base already carries part of the contract: {sorted(set(a for _, a in CONTRACT) - set(absent))}"
    )
    assert SECTION not in base, "the base must not carry the new section heading"
    print(f"  RED on {BASE_SHA[:12]}: {len(absent)} clause(s) absent")


def test_the_guard_is_green_on_the_working_tree() -> None:
    """The real, checked-in skill carries every clause of the owner's directive."""
    text = SKILL.read_text(encoding="utf-8")
    missing = _missing(text)
    assert not missing, f"planner skill is missing: {', '.join(missing)}"
    assert SECTION in text, f"the parallel dispatch section {SECTION!r} is absent"
    print(f"  GREEN on the head: all {len(CONTRACT)} clause(s) present")


def test_each_clause_is_named_in_the_dispatch_section() -> None:
    """The clauses are an ordered contract, not a scattered mention elsewhere."""
    text = SKILL.read_text(encoding="utf-8")
    assert SECTION in text, "no section to scope the clauses to"
    section = text.split(SECTION, 1)[1].split("\n## ", 1)[0]
    missing = _missing(section)
    assert not missing, f"clauses outside the dispatch section: {', '.join(missing)}"
    for needle, _ in CONTRACT:
        assert section.count(needle) == 1, f"clause {needle!r} is not stated exactly once"
    print("  every clause sits once inside the dispatch section")


def test_the_contract_keeps_the_existing_guardrails() -> None:
    """Parallel dispatch does not drop the claim/comment/merge discipline."""
    text = SKILL.read_text(encoding="utf-8")
    for needle, why in (
        ("Dispatch lanes in PARALLEL whenever their target files differ", "the earlier #1644 rule"),
        ("CLAIMS=", "the shared-file serialisation seam"),
        ("Comment on the issue BEFORE you do the work.", "comment-before-work"),
        ("Claim twice before starting (race guard).", "claim-twice race guard"),
        ("A PR is never the handover.", "issue-thread handover"),
        ("No cron and no Actions schedule", "no cron / no Actions schedule"),
        ("NEVER merges", "the planner never merges"),
    ):
        assert needle in text, f"the landed contract dropped {why}: {needle!r}"
    print("  existing parallel, claim and no-merge guardrails survive")


def test_the_guard_is_discovered_and_called() -> None:
    """`make test` executes this module, and main() calls every test_* in it."""
    proc = subprocess.run(
        ["bash", str(RUNNER), "--list"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    assert proc.returncode == 0, f"runner --list failed: {proc.stderr[:300]}"
    listed = [Path(line).name for line in proc.stdout.splitlines() if line.strip()]
    assert Path(__file__).name in listed, (
        f"{Path(__file__).name} is not among the {len(listed)} modules the ONE runner lists"
    )
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    defs = [n.name for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
    main_fn = next((n for n in tree.body
                    if isinstance(n, ast.FunctionDef) and n.name == "main"), None)
    assert main_fn is not None, "the module has no main() runner"
    used = {n.id for n in ast.walk(main_fn) if isinstance(n, ast.Name)}
    uncalled = [name for name in defs if name not in used]
    assert not uncalled, f"test_* never called from main(): {uncalled}"
    assert "raise SystemExit(main())" in source, "the module must exit non-zero on failure"
    print(f"  runner lists it; main() calls all {len(defs)} test_* functions")


def main() -> int:
    print("parallel planner dispatch guard (issue #1767)")
    failed = 0
    for fn in (
        test_the_guard_is_red_on_the_fetched_base,
        test_the_guard_is_green_on_the_working_tree,
        test_each_clause_is_named_in_the_dispatch_section,
        test_the_contract_keeps_the_existing_guardrails,
        test_the_guard_is_discovered_and_called,
    ):
        try:
            fn()
        except AssertionError as exc:
            failed += 1
            print(f"  FAIL {fn.__name__}: {exc}")
    print(f"\nPASSED {5 - failed} | FAILED {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
