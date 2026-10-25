#!/usr/bin/env python3
"""Every agent leg runs from a project skill, and an unattended leg never asks (issue #549).

Measured on the issue-bot sweep: three of five runs on 2026-10-24/25 died with
`Input required; detached without cancelling` (rc=3). `--yolo --accept-hooks` answers shell and
hook prompts, but NOT the agent's own `clarify` tool, so a run that asked a question exited with the
tree untouched and the pipeline reported "produced no implementation" over an agent that never ran.

These lock the seam that prevents it, over the REAL files and with the REAL gate running:

  1. every `hermes -z` leg preloads its own skill AND `bot-unattended`;
  2. every skill it names exists, its frontmatter `name` matches its directory, and it carries
     `## Inputs`, `## Output`, `## Rules`;
  3. the unattended contract is written ONCE (in the skill) and never inlined in a recipe;
  4. the gate FAILS on each of those defects, proved on a copy of the tree (never on the repo);
  5. `_setup` registers the directory and reads it back, or `hermes -s` resolves nothing;
  6. the workflows name rc=3 as "the agent asked for input", before their generic failure text;
  7. the gate is reachable from `make lint` (rule 6d) and from the suite (rule 6m).

Run standalone: python3 tests/test_agent_skills.py   or   make test
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check_agent_skills as CAS  # noqa: E402

SKILLS = ROOT / ".hermes" / "skills"
UNATTENDED = "never ask a question"
_PASS = 0
_FAIL = 0


def check(name: str, cond: bool, detail: object = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name} {detail}")


def _tree(td: Path, makefile: str, skills: dict[str, str] | None = None) -> Path:
    """A minimal tree the real gate can read: a Makefile, skills, AGENTS.md."""
    root = td / "repo"
    (root / ".hermes" / "skills").mkdir(parents=True)
    (root / "Makefile").write_text(makefile, encoding="utf-8")
    (root / "AGENTS.md").write_text("# rules\n", encoding="utf-8")
    # the gate asserts its contract-free probe exemption is real, so the fixture carries it
    (root / "scripts").mkdir()
    (root / "scripts" / "hermes_smoke.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    for name, body in (skills or {}).items():
        d = root / ".hermes" / "skills" / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(body, encoding="utf-8")
    return root


GOOD_SKILL = "---\nname: {name}\ndescription: d\n---\n\n## Inputs\n- x\n\n## Output\n- y\n\n## Rules\n- z\n"
SEAM = "# " + CAS.MAKEFILE_MARKER + "\n_hermes-skills-register:\n\t@true\n"


def test_the_real_legs_preload_a_real_skill():
    mk = (ROOT / "Makefile").read_text()
    found = CAS.legs(mk)
    check("legs: the Makefile carries the agent legs (guard not vacuous)", len(found) >= 8, len(found))
    for target, recipe in sorted(found.items()):
        names = CAS.preloaded(recipe)
        check(f"leg {target}: preloads a skill", bool(names), recipe[:120])
        check(f"leg {target}: preloads {CAS.UNATTENDED_SKILL}", CAS.UNATTENDED_SKILL in names, names)
        for name in names:
            path = SKILLS / name / "SKILL.md"
            check(f"leg {target}: skill `{name}` exists", path.is_file(), str(path))
            if path.is_file():
                fields, body = CAS.skill_meta(path)
                check(f"leg {target}: `{name}` frontmatter name matches its directory",
                      fields.get("name") == name, fields.get("name"))
                for section in CAS.REQUIRED_SECTIONS:
                    check(f"leg {target}: `{name}` carries `{section}`", section in body, "")


def test_the_unattended_contract_lives_in_one_place():
    mk = (ROOT / "Makefile").read_text()
    check("contract: the Makefile never inlines the unattended rule", UNATTENDED not in mk.lower())
    skill = (SKILLS / CAS.UNATTENDED_SKILL / "SKILL.md").read_text()
    check("contract: the skill states it", UNATTENDED in skill.lower())
    check("contract: it names the measured failure (rc=3 detached)",
          "detached" in skill and "3" in skill)
    hits = [p.parent.name for p in SKILLS.glob("*/SKILL.md") if UNATTENDED in p.read_text().lower()]
    check("contract: exactly one skill carries it", hits == [CAS.UNATTENDED_SKILL], hits)


def test_the_real_tree_passes_the_gate():
    findings = CAS.check(ROOT)
    check("gate: the shipped tree is green", findings == [], findings)


def test_the_gate_fails_each_defect():
    good = GOOD_SKILL
    base_skills = {CAS.UNATTENDED_SKILL: good.format(name=CAS.UNATTENDED_SKILL),
                   "data-search": good.format(name="data-search")}
    leg = ('\thermes -z "pointer" \\\n\t\t-m $(HERMES_ALIAS) --reasoning none '
           '$(HERMES_NONINTERACTIVE) -s data-search,bot-unattended\n')

    # Given a tree whose one leg is wired correctly
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), SEAM + f"search:\n{leg}", base_skills)
        check("gate: a correct tree is green (the fixture can pass)", CAS.check(root) == [], CAS.check(root))

    cases = {
        "a leg that preloads nothing": (SEAM + "search:\n\thermes -z \"pointer\" \\\n"
                                        "\t\t-m $(HERMES_ALIAS) --reasoning none $(HERMES_NONINTERACTIVE)\n",
                                        base_skills),
        "a leg naming a skill that does not exist": (SEAM + "search:\n" + leg.replace(
            "data-search", "no-such-skill"), base_skills),
        "a leg that inlines the unattended contract": (SEAM + "search:\n" + leg.replace(
            '"pointer"', f'"pointer {UNATTENDED}"'), base_skills),
        "a skill whose frontmatter name disagrees with its directory": (
            SEAM + "search:\n" + leg,
            {CAS.UNATTENDED_SKILL: good.format(name="other"),
             "data-search": good.format(name="data-search")}),
        "a skill that lost its Rules section": (
            SEAM + "search:\n" + leg,
            {CAS.UNATTENDED_SKILL: good.format(name=CAS.UNATTENDED_SKILL),
             "data-search": "---\nname: data-search\n---\n\n## Inputs\n- x\n\n## Output\n- y\n"}),
        "a Makefile with no registration target": (
            "# " + CAS.MAKEFILE_MARKER + "\nsearch:\n" + leg, base_skills),
        "a Makefile that lost the seam documentation": (
            "_hermes-skills-register:\n\t@true\nsearch:\n" + leg, base_skills),
        "a leg whose prompt grew back into a rulebook": (
            SEAM + "search:\n" + leg.replace('"pointer"', '"' + "x" * 4000 + '"'), base_skills),
    }
    for name, (mk, skills) in cases.items():
        with tempfile.TemporaryDirectory() as td:
            root = _tree(Path(td), mk, skills)
            check(f"gate: fails on {name}", CAS.check(root) != [], "the gate stayed green")


def test_setup_registers_the_directory_and_reads_it_back():
    mk = (ROOT / "Makefile").read_text()
    setup = mk.split("\n_setup:\n", 1)[1].split("\n.PHONY", 1)[0] if "\n_setup:\n" in mk else ""
    check("setup: registers the skills directory", "_hermes-skills-register" in setup, setup[-200:])
    check("setup: reads it back (a container where -s resolves nothing is loud)",
          "_hermes-skills-check" in setup, setup[-200:])
    # The real script, on a real temp home: register → --check passes; a fresh home fails.
    script = ROOT / "scripts" / "hermes_skills_register.py"
    with tempfile.TemporaryDirectory() as td:
        home = Path(td) / "hermes"
        p = subprocess.run([sys.executable, str(script), "--home", str(home), "--dir", str(SKILLS),
                            "--check"], capture_output=True, text=True)
        check("register: --check fails on an unregistered home (exit 1)", p.returncode == 1,
              f"rc={p.returncode} {p.stderr[-200:]}")
        p = subprocess.run([sys.executable, str(script), "--home", str(home), "--dir", str(SKILLS)],
                           capture_output=True, text=True)
        check("register: writes the directory", p.returncode == 0, p.stderr[-200:])
        p = subprocess.run([sys.executable, str(script), "--home", str(home), "--dir", str(SKILLS),
                            "--check"], capture_output=True, text=True)
        check("register: --check passes afterwards (exit 0)", p.returncode == 0, p.stderr[-200:])
        cfg = (home / "config.yaml").read_text()
        check("register: the value is a real YAML list (not an opaque string)",
              "external_dirs:" in cfg and "- " + str(SKILLS) in cfg, cfg[-200:])
        # a second registration is idempotent, never a duplicate entry
        subprocess.run([sys.executable, str(script), "--home", str(home), "--dir", str(SKILLS)],
                       capture_output=True, text=True)
        check("register: idempotent", (home / "config.yaml").read_text().count(str(SKILLS)) == 1,
              (home / "config.yaml").read_text())
        p = subprocess.run([sys.executable, str(script), "--home", str(home), "--dir",
                            str(Path(td) / "missing")], capture_output=True, text=True)
        check("register: a missing directory is a loud exit 2, never a silent pass",
              p.returncode == 2, p.returncode)


def test_the_workflows_name_rc_3_as_a_question():
    wf = ROOT / ".github" / "workflows"
    issue = (wf / "issue-bot.yml").read_text()
    check("issue-bot: names rc=3 as the agent asking for input",
          'RC:-}" = "3"' in issue and "asked for input" in issue)
    check("issue-bot: that branch comes BEFORE the generic 'produced no implementation'",
          0 <= issue.find('RC:-}" = "3"')
          < issue.find("::error::issue-bot produced no implementation"))
    review = (wf / "issue-review-bot.yml").read_text()
    check("issue-review-bot: both paths name rc=3",
          review.count('rc" = "3"') == 2 and "asked for input" in review,
          review.count('rc" = "3"'))
    check("the failure text points at the seam, not at the data",
          "bot-unattended" in issue and "#549" in issue)


def test_the_gate_is_wired_to_the_lint_target_and_the_suite():
    mk = (ROOT / "Makefile").read_text()
    m = re.search(r"\nlint: ##[^\n]*\n((?:\t[^\n]*\n)+)", mk)
    lint = m.group(1) if m else ""
    check("make lint: runs the agent-skills gate", "check-agent-skills" in lint, lint)
    check("make: the public gate target exists",
          "check-agent-skills:\n\tpython3 scripts/check_agent_skills.py check" in mk)
    check("make: the report target exists", "agent-skills-report:" in mk)
    check("suite: this module runs in `make test`", _wired(), "")
    # `make lint` really executes it: the target is called, not just mentioned.
    p = subprocess.run(["make", "-n", "lint"], cwd=str(ROOT), capture_output=True, text=True)
    check("make -n lint: the gate command is in the executed recipe",
          "check_agent_skills.py check" in p.stdout, p.stdout[-300:])


def _wired() -> bool:
    """The runner discovers `tests/test_*.py`; prove this file is in that set."""
    runner = ROOT / "scripts" / "run_tests.sh"
    p = subprocess.run(["bash", str(runner), "--list"], capture_output=True, text=True)
    return Path(__file__).name in p.stdout


def main() -> int:
    print("agent-leg skills (issue #549)")
    for fn in (test_the_real_legs_preload_a_real_skill,
               test_the_unattended_contract_lives_in_one_place,
               test_the_real_tree_passes_the_gate,
               test_the_gate_fails_each_defect,
               test_setup_registers_the_directory_and_reads_it_back,
               test_the_workflows_name_rc_3_as_a_question,
               test_the_gate_is_wired_to_the_lint_target_and_the_suite):
        print(f"-- {fn.__name__}")
        fn()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
