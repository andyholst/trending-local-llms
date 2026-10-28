#!/usr/bin/env python3
"""Behavioural tests for scripts/architecture_check.py + ARCHITECTURE.md (rule 6h, issue #178).

`ARCHITECTURE.md` describes every make target, pipeline, image and script, and
the checker is what keeps that true. These tests drive the REAL checker against
fixture trees (one failure mode each) and against the real repository, then
assert the wiring: the check runs in CI, in the fix loop and in this suite, and
the implementer prompt requires the update.

Wired into `make test` (rule 6d).
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from wiring import wired  # noqa: E402  (issues #176/#192)

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "architecture_check.py"

_PASS = 0
_FAIL = 0


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def _module():
    spec = importlib.util.spec_from_file_location("architecture_check", SCRIPT)
    assert spec and spec.loader, SCRIPT
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _tree(td: Path, targets=("build", "verify"), doc_targets=("build", "verify"),
          workflows=("ci.yml",), scripts=("thing.py",), doci_wf=True, doc_script=True,
          doc_roles=None, jobs=("build",), doc_jobs=None,
          validate_stages=None, only=(), agents_workflows=None):
    """A minimal repo fixture: Makefile + ARCHITECTURE.md + AGENTS.md + workflows + scripts.

    `doc_roles` writes the §6 script table: since issue #506 a script needs a ROLE
    there, and naming it in the generated §10 block does not count.
    `jobs` / `doc_jobs` are the workflow's real jobs and the §4 job names claimed
    for it; `validate_stages` writes a `scripts/validate.py` registering them and
    `only` writes `--only` lists into the fixture Makefile (issue #182).
    `agents_workflows` is the §6b list in the fixture `AGENTS.md` (rule 6h): it
    defaults to the workflows in the fixture tree, i.e. the shape the rule requires.
    """
    (td / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    (td / "scripts").mkdir(parents=True, exist_ok=True)
    if validate_stages is not None and "validate.py" not in scripts:
        scripts = tuple(scripts) + ("validate.py",)
    only_target = "".join(f"validate-list:\n\tpython3 scripts/validate.py --only {o}\n" for o in only)
    (td / "Makefile").write_text(
        ".PHONY: build verify\n" + "".join(f"{t}:\n\techo {t}\n" for t in targets) + only_target,
        encoding="utf-8",
    )
    # The RULEBOOK's pipeline list (§6b, rule 6h): one line per pipeline, each
    # naming the rule it enforces — the shape the section itself requires.
    listed = tuple(workflows) if agents_workflows is None else tuple(agents_workflows)
    agents_body = ["# AGENTS.md — fixture", "", "## 6b. The pipelines",
                   "", "`ARCHITECTURE.md` §4 is canonical for a pipeline's shape.", ""]
    agents_body += [f"- **`{w}`** — a pipeline (rule 6c)." for w in listed]
    agents_body += ["", "## 7. Style", "", "- Terse.", ""]
    (td / "AGENTS.md").write_text("\n".join(agents_body), encoding="utf-8")

    for w in workflows:
        (td / ".github" / "workflows" / w).write_text(
            "name: ci\njobs:\n" + "".join(f"  {j}:\n    runs-on: ubuntu-latest\n" for j in jobs),
            encoding="utf-8")
    for s in scripts:
        (td / "scripts" / s).write_text("# fixture\n", encoding="utf-8")
    if validate_stages is not None:
        adds = "".join(f'    add("a check", "{s}", lambda: None)\n' for s in validate_stages)
        (td / "scripts" / "validate.py").write_text(
            "def main():\n    checks = []\n\n    def add(label, name, fn):\n"
            "        checks.append((label, fn))\n" + adds, encoding="utf-8")
    rows = "\n".join(f"| `{t}` | does the thing |" for t in doc_targets)
    body = [f"# ARCHITECTURE", "", "## 3. Every `make` target", "", "| Target | What |", "|---|---|", rows, ""]
    body += ["## 4. Pipelines", ""]
    if doci_wf:
        body += [f"- `.github/workflows/{w}` — a pipeline" for w in workflows]
    if doc_script:
        body += [f"- `scripts/{s}` — a script" for s in scripts]
    claimed = jobs if doc_jobs is None else doc_jobs
    if doci_wf:
        for w in workflows:
            body += ["", f"### `.github/workflows/{w}` — a pipeline", "", "| Job | Does |", "|---|---|"]
            body += [f"| `{j}` | does it |" for j in claimed]
    body += ["", "## 6. The scripts", "", "| Script | Role |", "|---|---|"]
    if doc_script if doc_roles is None else doc_roles:
        body += [f"| `scripts/{s}` | what it does |" for s in scripts]
    body += ["", "## 7. Guards", ""]
    (td / "ARCHITECTURE.md").write_text("\n".join(body) + "\n", encoding="utf-8")
    return td



def test_missing_doc_is_a_failure():
    """No ARCHITECTURE.md at all is the loudest finding."""

    # Given a tree without the description
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "Makefile").write_text("build:\n\techo x\n", encoding="utf-8")

        # When  the checker runs on it
        problems = _module().findings(root)

    # Then  it says the file is part of the change
    check("missing doc: it is reported", any("ARCHITECTURE.md is missing" in p for p in problems), problems)


def test_undocumented_target_is_reported():
    """A make target the description does not name fails."""

    # Given a Makefile with a target the doc's tables omit
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), targets=("build", "verify", "new-thing"))

        # When  the checker runs
        problems = _module().findings(root)

    # Then  the undocumented target is named
    check("undocumented target: reported",
          any("`new-thing` is not described" in p for p in problems), problems)


def test_stale_target_mention_is_reported():
    """A target the description still claims, but the Makefile no longer has, fails."""

    # Given a doc row for a target that was removed
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), targets=("build",), doc_targets=("build", "gone-target"))

        # When  the checker runs
        problems = _module().findings(root)

    # Then  the stale claim is named
    check("stale target: reported",
          any("`gone-target`" in p and "no longer a make target" in p for p in problems), problems)


def test_undocumented_workflow_and_script_are_reported():
    """A workflow or a script that the description never mentions fails."""

    # Given a workflow and a script the doc does not describe
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), workflows=("ci.yml", "extra.yml"), scripts=("thing.py", "other.sh"),
                     doci_wf=False, doc_script=False)

        # When  the checker runs
        problems = _module().findings(root)

    # Then  both are named
    check("undocumented workflow: reported",
          any("workflow `extra.yml` is not described" in p for p in problems), problems)
    check("undocumented script: reported",
          any("script `scripts/other.sh` is not described" in p for p in problems), problems)


def test_phantom_reference_is_reported():
    """A workflow/script path the description names but the repo does not have fails."""

    # Given a doc that references a file which does not exist
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td))
        doc = root / "ARCHITECTURE.md"
        doc.write_text(doc.read_text() + "- `.github/workflows/ghost.yml` — gone\n"
                       + "- `scripts/ghost.sh` — gone\n", encoding="utf-8")

        # When  the checker runs
        problems = _module().findings(root)

    # Then  both phantom references are named
    check("phantom workflow: reported",
          any("ghost.yml" in p and "does not exist" in p for p in problems), problems)
    check("phantom script: reported",
          any("ghost.sh" in p and "does not exist" in p for p in problems), problems)


def test_fixture_tree_passes_when_in_step():
    """A tree whose description matches it exits 0 (the checker is not vacuous)."""

    # Given a consistent fixture tree
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td))

        # When  the checker runs as a subprocess
        proc = subprocess.run([sys.executable, str(SCRIPT), "--root", str(root)],
                              cwd=ROOT, capture_output=True, text=True)

    # Then  it exits 0
    check("consistent fixture: exit 0", proc.returncode == 0, proc.stdout + proc.stderr)


def test_real_repo_description_is_current():
    """This repository's own ARCHITECTURE.md describes everything it has."""

    # Given the real repository
    proc = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, capture_output=True, text=True)

    # When  the checker runs on it
    # Then  it is green, and the file names the pipelines and the key targets
    check("real repo: architecture-check exits 0", proc.returncode == 0, proc.stdout + proc.stderr)
    doc = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
    for needle in (".github/workflows/refresh-bot.yml", "issue-bot.yml", "qa-validate.yml",
                   "fix-bot.yml", "`refresh`", "`openspec-check`", "`data-gap-issue`"):
        check(f"real repo: {needle} is documented", needle in doc, "")


def test_wired_into_ci_the_loop_the_suite_and_the_prompt():
    """The check is reachable where it matters (rule 6d / rule 6h)."""

    # Given the Makefile, the PR pipeline, the fix loop and the implementer prompt
    mk = (ROOT / "Makefile").read_text()
    qa = (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text()
    loop = (ROOT / "scripts" / "fix_loop.sh").read_text()
    prompt = mk.split("_implement-issue:")[1][:6000]
    # Issue #549: the implementer's rules are its project skill; the recipe is a pointer.
    skill = (ROOT / ".hermes" / "skills" / "issue-implement" / "SKILL.md").read_text()

    # When  their wiring is read
    # Then  the target exists, CI + the loop run it, the suite carries this file, and the prompt demands the update
    check("make: the architecture-check target exists",
          "architecture-check:" in mk and "python3 scripts/architecture_check.py" in mk, "")
    check("ci: qa-validate's validate job runs it", "make architecture-check" in qa, "")
    check("loop: the fix loop runs it before the network-bound validate",
          "architecture-check" in loop, "")
    check("make: this test file runs in the suite",
          wired(__file__), "")
    check("prompt: the implementer must update ARCHITECTURE.md (rule 6h)",
          "ARCHITECTURE.md" in skill and "make architecture-check" in skill, skill[:300])
    check("prompt: the recipe preloads the implementer's skill (issue #549)",
          "-s issue-implement,bot-unattended" in prompt, prompt[:300])


def test_a_script_named_only_in_the_generated_block_has_no_role():
    """#506: §10 naming every script satisfied the old rule while §6 lost 9 of 46."""

    # Given a script the document names in §4 but gives no §6 row
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), scripts=("thing.py",), doc_roles=False)

        # When  the checker runs
        problems = _module().findings(root)

        # Then  it is reported as having no role, naming the section
        # And   fixing the row turns it green
        check("section 6: a script with no row is reported",
              any("scripts/thing.py" in p and "no row" in p for p in problems), problems)
        _tree(root, scripts=("thing.py",))
        check("section 6: the row makes it green", not _module().findings(root))


def test_validate_only_stage_lists_match_the_validator():
    """#182: a `--only` list is a claim about scripts/validate.py's stage map."""

    # Given a Makefile whose --only list names a stage the validator does not register
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), validate_stages=("data", "schema"), only=("data,gone",))

        # When  the checker runs
        problems = _module().findings(root)

    # Then  the unregistered stage is named, and so is the stage no list selects
    check("stages: an unregistered stage is reported",
          any("`--only gone`" in p and "does not register" in p for p in problems), problems)
    check("stages: a registered stage selected by no list is reported",
          any("stage `schema`" in p and "selected by no `--only` list" in p for p in problems), problems)

    # And   the same fixture with the list corrected reports neither
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), validate_stages=("data", "schema"), only=("data,schema",))
        problems = _module().findings(root)
    check("stages: the corrected list is green",
          not any("--only" in p or "selected by no" in p for p in problems), problems)


def test_pipeline_job_names_match_the_workflow_job_keys():
    """#182: §4's job lists are a claim about the workflows' real `jobs:` keys."""

    # Given §4 naming a job the workflow does not define
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), jobs=("guard", "alarm"), doc_jobs=("guard", "alarm", "sweep"))

        # When  the checker runs
        problems = _module().findings(root)

    # Then  the invented job is named with its workflow
    check("jobs: an invented job is reported",
          any("`sweep` in `ci.yml`" in p and "does not define" in p for p in problems), problems)

    # And   a real job no §4 section names
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), jobs=("guard", "review"), doc_jobs=("guard",))
        problems = _module().findings(root)
    check("jobs: an undescribed job is reported",
          any("job `review` is not named" in p for p in problems), problems)

    # And   a workflow with no §4 section of its own (so the coverage cannot be vacuous)
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), jobs=("guard",))
        doc = root / "ARCHITECTURE.md"
        doc.write_text(doc.read_text().replace(
            "### `.github/workflows/ci.yml` — a pipeline", "Pipeline prose"), encoding="utf-8")
        problems = _module().findings(root)
    check("jobs: a workflow with no §4 section is reported",
          any("no §4 section of its own" in p for p in problems), problems)

    # And   the fixture in step reports nothing about jobs
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), jobs=("guard", "alarm"), doc_jobs=("guard", "alarm"))
        problems = _module().findings(root)
    check("jobs: the corrected fixture is green",
          not any("does not define" in p or "is not named" in p or "no §4 section" in p
                  for p in problems), problems)


def test_doc_states_what_the_guard_does_not_prove():
    """#182: the boundary is part of the promise, in the doc and in the guard."""

    # Given the description and the guard's own docstring
    doc = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
    module_doc = _module().__doc__ or ""

    # When  the boundary is read
    # Then  it names what is proved, what is not, and the two structure claims
    check("boundary: the doc states what the guard proves",
          "What the guard proves — and what it does not" in doc, "")
    check("boundary: the doc says a wrong sentence about a real target passes",
          "cannot read prose" in doc, "")
    check("boundary: the two structural claims are named",
          "`--only`" in doc and "`jobs:`" in doc, "")
    check("boundary: the guard's own docstring states it", "cannot read prose" in module_doc, "")


def _rulebook_body() -> str:
    """`AGENTS.md` §6b, read with the checker's OWN section markers."""
    mod = _module()
    return mod.section((ROOT / "AGENTS.md").read_text(encoding="utf-8"),
                       mod.RULEBOOK_SECTION, mod.RULEBOOK_NEXT_SECTION)


def _rulebook_bullets() -> dict[str, str]:
    """`{workflow: bullet text}` for the pipeline bullets in §6b."""
    body = _rulebook_body()
    out: dict[str, str] = {}
    for block in re.split(r"\n(?=- \*\*`)", body):
        m = re.match(r"- \*\*`([A-Za-z0-9_.-]+\.yml)`\*\*", block)
        if m:
            out[m.group(1)] = block
    return out


def test_a_pipeline_missing_from_the_rulebook_is_reported():
    """rule 6h: a workflow in the tree that `AGENTS.md` §6b never names fails."""

    # Given a tree whose §6b names only ci.yml while the workflows dir holds two
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), workflows=("ci.yml", "extra.yml"),
                     agents_workflows=("ci.yml",))

        # When  the checker runs
        problems = _module().findings(root)

    # Then  the unlisted pipeline is named against the rulebook's section
    check("rulebook: an unlisted pipeline is reported",
          any("workflow `extra.yml` is not named in AGENTS.md §6b" in p for p in problems),
          problems)

    # And   the same tree with a §6b line naming it is green in that direction
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), workflows=("ci.yml", "extra.yml"),
                     agents_workflows=("ci.yml", "extra.yml"))
        problems = _module().findings(root)
    check("rulebook: naming it turns that finding green",
          not any("§6b" in p for p in problems), problems)


def test_a_rulebook_line_with_no_workflow_is_reported():
    """rule 6h: §6b naming a `.yml` that is not a workflow is the other direction."""

    # Given a §6b line for a workflow the tree does not hold
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), workflows=("ci.yml",),
                     agents_workflows=("ci.yml", "ghost.yml"))

        # When  the checker runs
        problems = _module().findings(root)

    # Then  the phantom §6b line is named as such
    check("rulebook: a line with no workflow is reported",
          any("AGENTS.md §6b names `ghost.yml`" in p and "not a workflow" in p
              for p in problems), problems)
    check("rulebook: the real workflow is not blamed for it",
          not any("workflow `ci.yml` is not named" in p for p in problems), problems)


def test_a_missing_agents_doc_is_a_finding_not_a_skip():
    """Deleting `AGENTS.md` cannot silence its own pipeline list (rule 6h)."""

    # Given a consistent fixture tree with its rulebook removed
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td))
        (root / "AGENTS.md").unlink()

        # When  the checker runs
        problems = _module().findings(root)

    # Then  the missing rulebook is a finding, never a clean pass
    check("rulebook: a missing AGENTS.md is a finding",
          any("AGENTS.md is missing" in p and "§6b" in p for p in problems), problems)


def test_the_rulebook_points_at_the_canonical_pipeline_description():
    """rule 6h: §6b says where a pipeline's SHAPE lives, and names the rule per pipeline."""

    # Given the real rulebook's §6b and the workflows it must cover
    body = _rulebook_body()
    bullets = _rulebook_bullets()
    workflows = sorted(p.name for p in (ROOT / ".github" / "workflows").glob("*.yml"))
    heading = next((ln for ln in body.splitlines() if ln.startswith("## 6b.")), "")

    # When  the section is read
    # Then  it points at §4 as canonical, claims no count, and each pipeline carries its rule
    check("rulebook: §6b names ARCHITECTURE.md §4 as canonical for a pipeline's shape",
          "ARCHITECTURE.md" in body and "§4" in body and "canonical" in body, body[:400])
    check("rulebook: §6b names every workflow in the tree",
          not [w for w in workflows if w not in bullets], str(sorted(bullets)))
    check("rulebook: every listed pipeline carries the rule it enforces",
          [w for w in workflows if w in bullets and "rule " not in bullets[w]],
          str(sorted(bullets)))
    check("rulebook: the §6b heading claims no pipeline count",
          not re.search(r"\b(Four|Five|Six|Seven|Eleven|Twelve|\d+)\s+pipelines?\b", heading),
          heading)


def test_rule_6h_names_the_rulebook_obligation():
    """rule 6h: a new workflow is named in §6b in the SAME change."""

    # Given §2 rule 6h
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    m = re.search(r"^6h\. \*\*.*?(?=^6i\. )", text, re.S | re.M)
    rule = m.group(0) if m else ""

    # When  a contributor adds a pipeline
    # Then  the rule tells them §6b must name it and that the guard fails otherwise
    check("rule 6h: the rule is found", bool(rule), text[:200])
    check("rule 6h: it names the §6b obligation", "§6b" in rule, rule[:400])
    check("rule 6h: the naming is in the SAME change and gated by architecture-check",
          "same change" in rule.lower() and "architecture-check" in rule, rule[:600])


def main() -> int:
    print("architecture description + its guard (ARCHITECTURE.md, rule 6h)")
    test_missing_doc_is_a_failure()
    test_undocumented_target_is_reported()
    test_stale_target_mention_is_reported()
    test_undocumented_workflow_and_script_are_reported()
    test_phantom_reference_is_reported()
    test_fixture_tree_passes_when_in_step()
    test_a_script_named_only_in_the_generated_block_has_no_role()
    test_validate_only_stage_lists_match_the_validator()
    test_pipeline_job_names_match_the_workflow_job_keys()
    test_a_pipeline_missing_from_the_rulebook_is_reported()
    test_a_rulebook_line_with_no_workflow_is_reported()
    test_a_missing_agents_doc_is_a_finding_not_a_skip()
    test_the_rulebook_points_at_the_canonical_pipeline_description()
    test_rule_6h_names_the_rulebook_obligation()
    test_doc_states_what_the_guard_does_not_prove()
    test_real_repo_description_is_current()
    test_wired_into_ci_the_loop_the_suite_and_the_prompt()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
