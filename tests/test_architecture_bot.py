#!/usr/bin/env python3
"""Behavioural tests for scripts/architecture_bot.py (issue #479, rule 6h).

`ARCHITECTURE.md` §10 is the LIVING half of the description: every pipeline with
its triggers, jobs and `make` targets, the product end to end, one line per
script. It is DERIVED from the tree — so these tests drive the real script
against fixture trees (one behaviour each) and against the real repository, then
assert the wiring: `make architecture-refresh` writes it, `make
architecture-check` refuses a stale block, and the daily pipeline runs both.

No mocks: every case runs the actual script in its own process and reads the file
it wrote.

Wired into `make test` (rule 6d).
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from wiring import wired  # noqa: E402  (issues #176/#192)

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "architecture_bot.py"
BEGIN = "<!-- architecture-bot:begin -->"
END = "<!-- architecture-bot:end -->"

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


def run(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args, "--root", str(root)],
                          capture_output=True, text=True)


def _tree(td: Path, workflows: dict[str, str] | None = None,
          targets: tuple[str, ...] = ("search", "merge", "render-readme"),
          doc_targets: bool = True) -> Path:
    """A minimal repo: Makefile + workflows + a script + README + data artifacts."""
    wf = td / ".github" / "workflows"
    wf.mkdir(parents=True, exist_ok=True)
    (td / "scripts").mkdir(parents=True, exist_ok=True)
    (td / "data" / "raw").mkdir(parents=True, exist_ok=True)
    (td / "data" / "snapshots").mkdir(parents=True, exist_ok=True)
    (td / "data" / "models.json").write_text("{}\n", encoding="utf-8")
    (td / "README.md").write_text("# Fixture\n\n## ❤️ Most loved\n\n### 8 GB\n\n## License\n",
                                 encoding="utf-8")
    (td / "scripts" / "update_trending.py").write_text(
        '#!/usr/bin/env python3\n"""Fold raw snapshots into the store."""\n', encoding="utf-8")
    (td / "Makefile").write_text(
        ".PHONY: " + " ".join(targets) + "\n"
        + "".join(f"{t}: ## {t} the thing\n\techo {t}\n" for t in targets),
        encoding="utf-8",
    )
    for name, text in (workflows or {"ci.yml": _workflow()}).items():
        (wf / name).write_text(text, encoding="utf-8")
    (td / "ARCHITECTURE.md").write_text(
        "# ARCHITECTURE\n\n## 3. Every `make` target\n\n| Target | What |\n|---|---|\n"
        + ("".join(f"| `{t}` | does it |\n" for t in targets) if doc_targets else "")
        + "\n## 4. The pipelines\n\n## 10. The living inventory\n\n"
        + f"{BEGIN}\n{END}\n", encoding="utf-8")
    return td


def _workflow(cron: str = "13 5 * * *", targets: tuple[str, ...] = ("merge",)) -> str:
    calls = "".join(f"          make {t}\n" for t in targets)
    return (
        "name: fixture-bot\n\n"
        "on:\n"
        "  schedule:\n"
        f'    - cron: "{cron}"\n'
        "  workflow_dispatch:\n\n"
        "# a comment that says `make nonsense` and must never be reported as a call\n"
        "jobs:\n"
        "  guard:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - run: echo guard\n"
        "  work:\n"
        "    needs: guard\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - name: do it\n"
        "        run: |\n"
        + calls
        + "          make not-a-target\n"
    )


def test_block_is_derived_from_the_tree():
    with tempfile.TemporaryDirectory() as d:
        root = _tree(Path(d))
        r = run(root, "--write")
        check("write: the script exits 0", r.returncode == 0, r.stderr.strip()[-200:])
        block = (root / "ARCHITECTURE.md").read_text(encoding="utf-8")
        check("block: every workflow is named", "`.github/workflows/ci.yml`" in block)
        check("block: the workflow's name is reported", "fixture-bot" in block)
        check("block: the cron slot is reported", "cron `13 5 * * *`" in block)
        check("block: the dispatch trigger is reported", "`workflow_dispatch`" in block)
        check("block: jobs are listed in file order with their needs",
              "`guard`, `work` (needs `guard`)" in block, block[block.find("**jobs:**"):][:160])
        check("block: a target a step calls is reported with the Makefile's description",
              "`make merge` — merge the thing" in block)
        check("block: prose in a workflow COMMENT is not reported as a call",
              "make nonsense" not in block)
        check("block: a `make` naming no real target is not reported",
              "not-a-target" not in block)
        check("block: one line per script, from its own docstring",
              "`scripts/update_trending.py` — Fold raw snapshots into the store." in block)
        check("block: the README sections are listed",
              "- ❤️ Most loved" in block and "- License" in block)
        check("block: the card tiers are not sections",
              "8 GB" not in block)
        check("block: the product end to end is a table naming real targets",
              "| 1. Search | make search |" in block and "| 4. Render |" in block)
        check("block: the flow says how a row reaches README.md",
              "README.md" in block and "render_readme" in block)
        check("check: the freshly written block passes", run(root, "--check").returncode == 0)


def test_check_is_red_on_a_stale_block_and_green_after_write():
    with tempfile.TemporaryDirectory() as d:
        root = _tree(Path(d))
        run(root, "--write")
        # the tree moves on: a second workflow appears and a target is added
        (root / ".github" / "workflows" / "new-bot.yml").write_text(
            _workflow("41 * * * *", ("render-readme",)), encoding="utf-8")
        r = run(root, "--check")
        check("stale: --check exits 1", r.returncode == 1, f"rc={r.returncode}")
        check("stale: it says the block is STALE", "STALE" in r.stderr, r.stderr[-200:])
        check("stale: it names what to run", "make architecture-refresh" in r.stderr)
        check("stale: --write then makes it green",
              run(root, "--write").returncode == 0 and run(root, "--check").returncode == 0)
        block = (root / "ARCHITECTURE.md").read_text(encoding="utf-8")
        check("stale: the new workflow is described after the rewrite",
              "new-bot.yml" in block)


def test_missing_markers_are_loud_and_write_nothing():
    with tempfile.TemporaryDirectory() as d:
        root = _tree(Path(d))
        doc = root / "ARCHITECTURE.md"
        doc.write_text("# ARCHITECTURE\n\nno markers here\n", encoding="utf-8")
        r = run(root, "--write")
        check("markers: --write refuses a document with no markers", r.returncode == 1)
        check("markers: it names what is missing", BEGIN in r.stderr)
        check("markers: the file is left untouched", doc.read_text() == "# ARCHITECTURE\n\nno markers here\n")
        r = run(root, "--check")
        check("markers: --check fails too", r.returncode == 1 and "no" in r.stderr.lower())


def test_a_flow_the_tree_does_not_back_is_refused():
    with tempfile.TemporaryDirectory() as d:
        root = _tree(Path(d))
        (root / "Makefile").write_text("search: ## s\n\techo\n", encoding="utf-8")
        r = run(root, "--check")
        check("flow: a renamed-away target fails the check", r.returncode == 1, r.stdout + r.stderr)
        check("flow: the failure names the target", "make merge" in r.stderr, r.stderr[-300:])
        r = run(root, "--write")
        check("flow: --write refuses to describe what is gone", r.returncode == 1)
        check("flow: and writes nothing", BEGIN + "\n" + END in (root / "ARCHITECTURE.md").read_text())


def test_real_repository_inventory_is_current():
    r = run(ROOT, "--check")
    check("repo: ARCHITECTURE.md's block matches the tree", r.returncode == 0, r.stderr[-400:])
    block = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
    workflows = sorted(p.name for p in (ROOT / ".github" / "workflows").glob("*.yml"))
    scripts = sorted(p.name for p in (ROOT / "scripts").glob("*") if p.is_file())
    missing_wf = [w for w in workflows if w not in block]
    missing_sc = [s for s in scripts if s not in block]
    check("repo: every pipeline is in the inventory", not missing_wf, str(missing_wf))
    check("repo: every script is in the inventory", not missing_sc, str(missing_sc))
    check("repo: the bot itself is described", "architecture-bot.yml" in block)
    check("repo: the flow names the merge that writes README.md",
          "make merge" in block and "README.md" in block)


def test_wired_into_the_makefile_the_guard_and_the_pipeline():
    mk = (ROOT / "Makefile").read_text(encoding="utf-8")
    check("wiring: make architecture-refresh writes the block",
          "architecture-refresh:" in mk and "scripts/architecture_bot.py --write" in mk)
    check("wiring: make architecture-check refuses a stale block",
          "scripts/architecture_bot.py --check" in mk)
    wf = (ROOT / ".github" / "workflows" / "architecture-bot.yml").read_text(encoding="utf-8")
    check("wiring: the daily pipeline runs the refresh through make",
          "make architecture-refresh" in wf)
    check("wiring: it proves the whole document", "make architecture-check" in wf)
    check("wiring: it asserts its base before cutting a branch (rule 6n)",
          "make base-check" in wf)
    check("wiring: the guard is its own FIRST job (rule 6j)",
          wf.index("  guard:") < wf.index("  refresh:"))
    check("wiring: the scheduled run passes the guard",
          'if [ "$EVENT" = "schedule" ]' in wf)
    check("wiring: the branch name cannot look like an issue reference",
          "TRAILING" not in wf and "%Y%m%dT%H%M%SZ" in wf)
    check("wiring: the PR body carries no closing keyword",
          "Closes #" not in wf and "closes #" not in wf)
    check("wiring: it never pushes master", "refs/heads/master" not in wf)
    check("wiring: it opens a PR only when the block changed",
          "steps.drift.outputs.changed == 'true'" in wf)
    check("wiring: the guard is registered in tests/test_workflows.py",
          '"architecture-bot.yml", "guard"' in (ROOT / "tests" / "test_workflows.py").read_text())
    check("wiring: qa-validate gates on the same check",
          "make architecture-check" in (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text())
    check("wiring: this module is discovered by the ONE test runner", wired(__file__))


def main() -> int:
    print("ARCHITECTURE.md's living inventory + its daily bot (scripts/architecture_bot.py)")
    test_block_is_derived_from_the_tree()
    test_check_is_red_on_a_stale_block_and_green_after_write()
    test_missing_markers_are_loud_and_write_nothing()
    test_a_flow_the_tree_does_not_back_is_refused()
    test_real_repository_inventory_is_current()
    test_wired_into_the_makefile_the_guard_and_the_pipeline()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
