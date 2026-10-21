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
          doc_roles=None):
    """A minimal repo fixture: Makefile + ARCHITECTURE.md + workflows + scripts.

    `doc_roles` writes the §6 script table: since issue #506 a script needs a ROLE
    there, and naming it in the generated §10 block does not count.
    """
    (td / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    (td / "scripts").mkdir(parents=True, exist_ok=True)
    (td / "Makefile").write_text(
        ".PHONY: build verify\n" + "".join(f"{t}:\n\techo {t}\n" for t in targets),
        encoding="utf-8",
    )
    for w in workflows:
        (td / ".github" / "workflows" / w).write_text("name: ci\n", encoding="utf-8")
    for s in scripts:
        (td / "scripts" / s).write_text("# fixture\n", encoding="utf-8")
    rows = "\n".join(f"| `{t}` | does the thing |" for t in doc_targets)
    body = [f"# ARCHITECTURE", "", "## 3. Every `make` target", "", "| Target | What |", "|---|---|", rows, ""]
    body += ["## 4. Pipelines", ""]
    if doci_wf:
        body += [f"- `.github/workflows/{w}` — a pipeline" for w in workflows]
    if doc_script:
        body += [f"- `scripts/{s}` — a script" for s in scripts]
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
          "ARCHITECTURE.md" in prompt and "make architecture-check" in prompt, prompt[:300])


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


def main() -> int:
    print("architecture description + its guard (ARCHITECTURE.md, rule 6h)")
    test_missing_doc_is_a_failure()
    test_undocumented_target_is_reported()
    test_stale_target_mention_is_reported()
    test_undocumented_workflow_and_script_are_reported()
    test_phantom_reference_is_reported()
    test_fixture_tree_passes_when_in_step()
    test_a_script_named_only_in_the_generated_block_has_no_role()
    test_real_repo_description_is_current()
    test_wired_into_ci_the_loop_the_suite_and_the_prompt()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
