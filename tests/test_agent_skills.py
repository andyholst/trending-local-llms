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

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check_agent_skills as CAS  # noqa: E402
import coverage_gap  # noqa: E402  (issue #1147: the ONE declared-coverage-gap seam)

SKILLS = ROOT / "agents" / "skills"
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
    (root / "agents" / "skills").mkdir(parents=True)
    (root / "Makefile").write_text(makefile, encoding="utf-8")
    (root / "AGENTS.md").write_text("# rules\n", encoding="utf-8")
    # the gate asserts its contract-free probe exemption is real, so the fixture carries it
    (root / "scripts").mkdir()
    (root / "scripts" / "hermes_smoke.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    for name, body in (skills or {}).items():
        d = root / "agents" / "skills" / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(body, encoding="utf-8")
    return root


GOOD_SKILL = "---\nname: {name}\ndescription: d\n---\n\n## Inputs\n- x\n\n## Output\n- y\n\n## Rules\n- z\n"
#: The retired rules (issue #638) must be stated by the skill they moved to, so a fixture tree whose
#: `data-search` skill lacks them is red for the right reason. This is the minimal carrier.
DATA_SEARCH_SKILL = GOOD_SKILL.format(name="data-search") + "".join(
    f"- {needle}\n" for needle in (
        "engine_repo", "system_ram_min", "execute_code", "/status/<id>", "reshares and views"))
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
                   "data-search": DATA_SEARCH_SKILL}
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
        # Issue #638: a rule retired into the skill may not be restated in a recipe, and a skill
        # that lost it is a contract with a hole in it.
        "a recipe that restates a retired rule": (
            SEAM + "search:\n" + leg.replace('"pointer"', '"pointer engine_repo"'), base_skills),
        "a skill that lost a retired rule": (
            SEAM + "search:\n" + leg,
            {CAS.UNATTENDED_SKILL: good.format(name=CAS.UNATTENDED_SKILL),
             "data-search": good.format(name="data-search")}),
        # Issue #194: the base image has no `gh`, so a container-bound contract that INSTRUCTS a
        # `gh` subcommand is unreachable code the agent can only fail on or skip silently.
        "a recipe that instructs the agent to run gh": (
            SEAM + "search:\n" + leg.replace(
                '"pointer"', '"pointer gh issue edit --add-label needs-refinement"'), base_skills),
        "a skill that instructs the agent to run gh": (
            SEAM + "search:\n" + leg,
            {CAS.UNATTENDED_SKILL: good.format(name=CAS.UNATTENDED_SKILL),
             "data-search": DATA_SEARCH_SKILL
             + "- gh pr comment $PR --body done\n"}),
    }
    for name, (mk, skills) in cases.items():
        with tempfile.TemporaryDirectory() as td:
            root = _tree(Path(td), mk, skills)
            check(f"gate: fails on {name}", CAS.check(root) != [], "the gate stayed green")


def test_the_gh_guard_refuses_instructions_and_keeps_forbiddances():
    """Issue #194: `gh <subcommand>` in a container-bound contract is a finding; a sentence
    stating gh is ABSENT is the contract itself and must not be one."""
    hits = CAS.gh_findings("fixture", "run gh issue edit --add-label x\n")
    check("gh-guard: an instruction to run gh is a finding", len(hits) == 1, hits)
    hits = CAS.gh_findings("fixture", "**You have no `gh` and no network write.** "
                                     "Do not comment, close, label, or edit anything;\n")
    check("gh-guard: a forbiddance stating gh is absent is not a finding", hits == [], hits)
    hits = CAS.gh_findings("fixture", "the container has no gh; forbid gh entirely\n")
    check("gh-guard: 'forbid gh' wording is not a finding", hits == [], hits)
    hits = CAS.gh_findings("fixture", "gh runs and gh api are both instructions\n")
    check("gh-guard: subcommand spellings are caught", len(hits) == 1, hits)
    check("gh-guard: the REAL tree instructs no gh anywhere a leg can read it",
          [h for t, r in CAS.legs((ROOT / "Makefile").read_text()).items()
           for h in CAS.gh_findings(t, r)] == []
          and all(CAS.gh_findings(str(p), p.read_text(encoding="utf-8")) == []
                  for p in sorted((ROOT / "agents" / "skills").glob("*/SKILL.md"))))


# ── the temp Hermes home seam (issue #1145) ──────────────────────────────────────────────
# Hermes 0.23.2 — the version this change pins — does not stop writing when its CLI exits: a
# `hermes config set` seeds `cache/uv`, `installs/<hash>` and `cache/default-plugins.*` behind
# itself, 4 s after the CLI returned (measured on the host). `tempfile.TemporaryDirectory`'s
# cleanup raced that pass and died `OSError: [Errno 39] Directory not empty: '<tmp>/hermes/cache'`
# — RED in CI's own `make test` (qa-validate run 44537216542) with every assertion green. The
# teardown seam lives ONCE in `tests/hermes_home.py` (rule 6d) and is used by every test that
# points Hermes at a temp home.
from hermes_home import remove_hermes_home, temp_hermes_home  # noqa: E402  (issue #1145)


def test_setup_registers_the_directory_and_reads_it_back():
    mk = (ROOT / "Makefile").read_text()
    setup = mk.split("\n_setup:\n", 1)[1].split("\n.PHONY", 1)[0] if "\n_setup:\n" in mk else ""
    check("setup: registers the skills directory", "_hermes-skills-register" in setup, setup[-200:])
    check("setup: reads it back (a container where -s resolves nothing is loud)",
          "_hermes-skills-check" in setup, setup[-200:])
    # The real script, on a real temp home: register → --check passes; a fresh home fails.
    # (issue #1154) the register half drives the REAL `hermes` CLI, which a host `make test`
    # does not have (no agent may dispatch a pipeline). That half is declared through the
    # coverage-gap seam — the runner names it in the verdict and the module stays green —
    # instead of going red with the CLI's own "not on PATH" message and a FileNotFoundError.
    if shutil.which("hermes") is None:
        coverage_gap.external_binary_gap(
            "hermes-skills register half",
            "hermes",
            "a host `make test` has no agent CLI; the container run drives the real one",
        )
        return
    script = ROOT / "scripts" / "hermes_skills_register.py"
    with temp_hermes_home() as td:
        home = td / "hermes"
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


def test_the_fixer_skill_names_the_openspec_failures():
    """issue #560: a skill that does not name the failure it is handed makes the agent ask — rc=3.

    fix-bot run 40177729642 burned all three rounds on `[openspec-tasks] FAIL …: unchecked task
    checkbox(es)`, and every round died with `Input required; detached without cancelling` because
    `pr-fix` said nothing about the OpenSpec gate. Before the seam landed the same loop went green
    in 1-2 rounds. The skill must name each OpenSpec failure and its remedy.
    """
    skill = (SKILLS / "pr-fix" / "SKILL.md").read_text()
    for needle, why in (
        ("unchecked task checkbox", "an unticked checklist is ticked only when its step is done"),
        ("make openspec-index", "a stale index is regenerated, never hand-edited"),
        ("openspec validate", "a spec that does not validate is fixed, not the check"),
        ("make openspec-archive", "a merged PR's change is archived, not edited"),
        ("never turned into a question", "the rule that keeps the run from detaching"),
    ):
        check(f"pr-fix skill names: {why}", needle in skill, needle)


def test_the_implement_skill_states_the_tick_rule():
    """(issue #658) The tick rule the pre-open gate enforces is stated in the skill itself."""
    skill = (SKILLS / "issue-implement" / "SKILL.md").read_text()
    flat = " ".join(skill.split())
    check("tick rule: a box is ticked ONLY when the tree proves the step",
          "ticked ONLY when the tree proves" in flat, flat[flat.find("tasks.md"):][:200])
    check("tick rule: an owed step is written `- [~] … — blocked:` at creation",
          "- [~]" in skill and "— blocked:" in skill, "")
    check("tick rule: the skill names the gate that refuses an open PR with `- [ ]`",
          "openspec-tasks-check" in skill, "")


def test_registered_markers_in_skills_are_checked_against_the_registry_itself():
    """(rule 6j, issue #904) A registered marker re-spelled inside a skill contract is a defect.

    The names AND their acceptance shapes are derived from `scripts/bot_markers.py` — the gate
    never re-spells a shape, so it cannot drift from the writers. The registry's own renderings
    pass; naming a marker in prose or backticks (no `<!--`) stays legal; the shipped tree is clean.
    """
    import bot_markers
    leg = ('\thermes -z "pointer" \\\n\t\t-m $(HERMES_ALIAS) --reasoning none '
           '$(HERMES_NONINTERACTIVE) -s data-search,bot-unattended\n')
    base = {CAS.UNATTENDED_SKILL: GOOD_SKILL.format(name=CAS.UNATTENDED_SKILL),
            "data-search": DATA_SEARCH_SKILL}

    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), SEAM + "search:\n" + leg, base)
        check("markers: a marker-free fixture has no marker findings",
              CAS.marker_findings(root) == [], CAS.marker_findings(root))

    # A skill that copies a registered marker's NAME but loses the registry's shape (no Z).
    respelled = GOOD_SKILL.format(name="issue-review") + (
        "- stamp `<!-- issue-review: 2026-01-01T00:00:00 -->` before writing\n")
    skills = dict(base, **{"issue-review": respelled})
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), SEAM + "search:\n" + leg, skills)
        findings = CAS.check(root)  # end to end: the gate itself, not just the scan
        hits = [f for f in findings if "issue-review" in f and "bot_markers.py" in f]
        check("markers: a re-spelled registered marker reds the gate", bool(hits), findings)
        check("markers: the finding names the file and line",
              bool(hits) and re.match(r"agents/skills/issue-review/SKILL\.md:\d+:", hits[0]),
              hits[0] if hits else "")

    # Every rendering the registry itself writes passes the scan — the acceptance patterns are
    # the registry's own grammar, not a second copy.
    canonical = GOOD_SKILL.format(name="issue-review") + "".join(
        f"- {ex}\n" for ex in bot_markers.canonical_examples())
    skills = dict(base, **{"issue-review": canonical})
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), SEAM + "search:\n" + leg, skills)
        check("markers: every canonical registry rendering stays green",
              CAS.marker_findings(root) == [], CAS.marker_findings(root))

    # Prose/backtick naming is not an occurrence.
    prose = GOOD_SKILL.format(name="issue-review") + (
        "- the `issue-review` marker opens the 3 h window (issue #411)\n")
    skills = dict(base, **{"issue-review": prose})
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), SEAM + "search:\n" + leg, skills)
        check("markers: naming a marker in prose stays legal",
              CAS.marker_findings(root) == [], CAS.marker_findings(root))

    shipped = CAS.marker_findings(ROOT)
    check("markers: the shipped agent skills carry no re-spelled registered marker",
          shipped == [], shipped[:4])


def test_registration_points_at_agents_skills_and_nothing_lives_in_dot_hermes():
    """(issue #904 reviewer ruling) `agents/skills` is the ONE home; `.hermes/skills` is retired.

    `_setup` registers agents/skills, the rulebook states it, and no Makefile, workflow or script
    spells the old path — a half-moved seam registers a directory that no longer exists and every
    `-s` then resolves NOTHING while reporting success.
    """
    mk = (ROOT / "Makefile").read_text()
    check("registration: HERMES_SKILLS_DIR points at agents/skills",
          "HERMES_SKILLS_DIR := $(CURDIR)/agents/skills" in mk)
    check("registration: the rulebook states agents/skills",
          "`agents/skills` is registered in the container's Hermes home" in (ROOT / "AGENTS.md").read_text())
    offenders: list[str] = []
    for p in sorted(list((ROOT / "scripts").glob("*"))
                    + list((ROOT / ".github" / "workflows").glob("*"))):
        if p.is_file() and p.suffix in {".py", ".sh", ".yml", ".yaml"}:
            if ".hermes/skills" in p.read_text(encoding="utf-8", errors="replace"):
                offenders.append(str(p.relative_to(ROOT)))
    check("no scripted contract or seam spells .hermes/skills", offenders == [], offenders)
    check("the old skills home is gone from the tree", not (ROOT / ".hermes" / "skills").exists())


def test_data_search_skill_names_the_measurement_alias_key():
    """The data-search skill states the attribution EXCEPTION, not only the refusal (issue #885).

    #652 made `measurement_model_aliases` the data home for a legitimate
    attribution exception and #884 made the search contract declare it, but a
    search leg reads only its preloaded skill (rule 6p): if the skill names
    only the refusal, the agent facing a legitimate exception cannot record it.
    Deleting the paragraph in agents/skills/data-search/SKILL.md reds this test.
    """
    skill = (SKILLS / "data-search" / "SKILL.md").read_text(encoding="utf-8")
    check("data-search names the exception key measurement_model_aliases",
          "measurement_model_aliases" in skill)
    check("it names the validator that checks the key",
          "check_measurement_alias_map" in skill)
    check("it states the key is row-level data",
          "on the ROW" in skill)


def test_the_temp_home_teardown_survives_a_writer_that_lands_after_the_caller_is_done():
    """The measured 0.23.2 shape: seeding lands AFTER the CLI returned, while teardown runs."""
    with temp_hermes_home() as td:
        home = td / "hermes"
        (home / "cache").mkdir(parents=True)
        (home / "config.yaml").write_text("seeded\n")
        import threading

        def seed() -> None:
            for i in range(20):
                time.sleep(0.1)
                try:
                    (home / "cache" / "uv").mkdir(exist_ok=True)
                    (home / "installs").mkdir(exist_ok=True)
                    (home / "installs" / f"{i}").write_text("x")
                    (home / "cache" / "default-plugins.settled").write_text("x")
                except OSError:
                    return

        t = threading.Thread(target=seed, daemon=True)
        t.start()
        # The writer is deliberately NOT joined: teardown must remove a home that is still
        # being seeded, exactly as the real CLI pass does.
        check("teardown: the home exists while a background seeder is still landing files",
              (home / "config.yaml").exists())
    check("teardown: a home whose seeder outlived the caller was still removed",
          not td.exists(), str(td))


def test_a_temp_home_that_never_becomes_removable_is_a_loud_failure_not_an_ignored_one():
    """The retry window must END in a loud failure, never in a swallowed one.

    Two halves, because the container `make test` runs in is not the host:
    `TEST_RUN` passes no `--user`, so the test container runs as the image's
    default user (root), and Linux `DAC_OVERRIDE` walks straight through a
    mode-0o000 directory — measured in CI: run 44551541279, where this plant was
    removed cleanly and the guard's own cleanup died `FileNotFoundError` on the
    path it had planted. So the ALWAYS-checked half uses a tree that never
    becomes removable for a reason no privilege can override (it is not there),
    and the permission half asserts only when the filesystem actually honours
    the plant — reported LOUDLY as a skip when it does not, never silently.
    """
    # Half 1 — every uid, every platform: retries exhausted == AssertionError,
    # and the bounded window returns instead of hanging.
    absent = Path(tempfile.mkdtemp()) / "hermes" / "installs"
    raised = False
    detail = "no AssertionError raised"
    try:
        remove_hermes_home(absent, attempts=3, delay=0.01)
    except AssertionError as exc:
        raised = True
        detail = str(exc)
    finally:
        shutil.rmtree(absent.parent.parent, ignore_errors=True)
    check("teardown: retries exhausted raise instead of being ignored", raised, detail)

    # Half 2 — a real stuck tree, when the filesystem honours the plant.
    td = Path(tempfile.mkdtemp())
    inner = td / "hermes" / "cache"
    inner.mkdir(parents=True)
    (inner / "locked").mkdir()
    os.chmod(inner, 0o000)
    try:
        os.listdir(inner)
        honored = False
    except PermissionError:
        honored = True
    if not honored:
        # (issue #1147) this line used to be a bare SKIP inside a module that exited 0: measured in
        # qa-validate run 44551541279, a green suite over a plant the container's uid 0 walked
        # straight through. A bypass now travels INSIDE the declared gap seam, so the runner names
        # it in the verdict instead of losing it in a passing module's deleted output.
        coverage_gap.declare_bypass_gap(
            "teardown permission half",
            "TEST_RUN runs the container as the image's default user; DAC_OVERRIDE walks a "
            "mode-0o000 dir; half 1 (the tree that never becomes removable) still locks its contract",
        )
        remove_hermes_home(td, attempts=3, delay=0.01)
        check("teardown: a privilege-bypassed plant is still removed", not td.exists(), str(td))
        return
    raised = False
    detail = "no AssertionError raised"
    try:
        remove_hermes_home(td, attempts=3, delay=0.01)
    except AssertionError as exc:
        raised = True
        detail = str(exc)
    finally:
        os.chmod(inner, 0o755) if inner.exists() else None
        shutil.rmtree(td, ignore_errors=True)
    check("teardown: a stuck tree raises instead of being ignored", raised, detail)


def main() -> int:
    print("agent-leg skills (issue #549)")
    for fn in (test_the_real_legs_preload_a_real_skill,
               test_the_unattended_contract_lives_in_one_place,
               test_the_real_tree_passes_the_gate,
               test_the_gate_fails_each_defect,
               test_setup_registers_the_directory_and_reads_it_back,
               test_the_temp_home_teardown_survives_a_writer_that_lands_after_the_caller_is_done,
               test_a_temp_home_that_never_becomes_removable_is_a_loud_failure_not_an_ignored_one,
               test_the_workflows_name_rc_3_as_a_question,
               test_the_gate_is_wired_to_the_lint_target_and_the_suite,
               test_the_fixer_skill_names_the_openspec_failures,
               test_the_implement_skill_states_the_tick_rule,
               test_the_gh_guard_refuses_instructions_and_keeps_forbiddances,
               test_registered_markers_in_skills_are_checked_against_the_registry_itself,
               test_registration_points_at_agents_skills_and_nothing_lives_in_dot_hermes,
               test_data_search_skill_names_the_measurement_alias_key):
        print(f"-- {fn.__name__}")
        fn()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
