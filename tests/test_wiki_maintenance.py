#!/usr/bin/env python3
"""RED-first behavioural tests for scripts/wiki_maintenance.py (issue #1773).

Every test drives the REAL script as a subprocess against a scratch tree, with
planted doc text. The rule: a CURRENT tree is green; a stale claim or an
obsolete doc is RED with the exact file+needle named. ``--apply`` composes a
keeper PR body that closes nothing and writes no doc. Wired into `make test`.
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from wiring import wired  # noqa: E402  (issues #176/#192)

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "wiki_maintenance.py"
PR_CLOSURE = ROOT / "scripts" / "pr_closure.py"
MAKEFILE = ROOT / "Makefile"
WORKFLOW = ROOT / ".github" / "workflows" / "refresh-bot.yml"

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


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *args],
        cwd=str(ROOT), capture_output=True, text=True,
    )


STORE = {
    "generated_utc": "2026-01-02T03:04:05Z",
    "note": "canonical store",
    "models": [{"name": "Alpha"}, {"name": "Beta"}],
}
CURRENT_STAMP = "2026-01-02 03:04"
README = (
    "# Board\n\n"
    f"> Last generated: {CURRENT_STAMP} UTC. Source: local mirror.\n\n"
    "## Rows\n\n"
    "|[**Alpha**](https://huggingface.co/x/alpha) | row |\n"
    "|[**Beta**](https://huggingface.co/x/beta) | row |\n"
)
ARCH = (
    "The living inventory.\n\n"
    "<!-- architecture-bot:begin -->\n"
    "- `scripts/alpha_tool.py` — the alpha tool.\n"
    "#### `.github/workflows/board.yml` — board\n"
    "<!-- architecture-bot:end -->\n"
)


def fixture(td: Path) -> Path:
    """A minimal, deterministic tree with all three truth sources present."""
    root = Path(td)
    (root / "data").mkdir()
    (root / "scripts").mkdir()
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / "data" / "models.json").write_text(json.dumps(STORE), encoding="utf-8")
    (root / "README.md").write_text(README, encoding="utf-8")
    (root / "ARCHITECTURE.md").write_text(ARCH, encoding="utf-8")
    (root / "scripts" / "alpha_tool.py").write_text("# alpha\n", encoding="utf-8")
    (root / ".github" / "workflows" / "board.yml").write_text("name: board\n", encoding="utf-8")
    return root


def doc_bytes(root: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in
            (root / "README.md", root / "ARCHITECTURE.md", root / "data" / "models.json")}


# --------------------------------------------------------------------------- tests

def test_a_current_tree_is_green():
    """A tree whose docs match the store is not reddened by the checker."""
    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td))
        proc = run(root, "--check")
    check("current tree: --check exits 0", proc.returncode == 0, proc.stdout + proc.stderr)
    check("current tree: reports OK", "OK:" in proc.stdout, proc.stdout)


def test_a_stale_render_stamp_is_a_false_claim_to_update():
    """GREEN on the current stamp, RED on a planted stale stamp, with file+needle."""
    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td))
        green = run(root, "--check")
        check("stamp: current stamp is green", green.returncode == 0, green.stdout)
        planted = "> Last generated: 2020-01-01 00:00 UTC. Source: local mirror."
        (root / "README.md").write_text(README.replace(
            f"> Last generated: {CURRENT_STAMP} UTC. Source: local mirror.", planted),
            encoding="utf-8")
        red = run(root, "--check")
    check("stamp: planted stale stamp is RED", red.returncode == 1, red.stdout + red.stderr)
    check("stamp: kind=false-claim", "kind=false-claim" in red.stdout, red.stdout)
    check("stamp: action=update", "action=update" in red.stdout, red.stdout)
    check("stamp: exact file", "file=README.md" in red.stdout, red.stdout)
    check("stamp: exact needle", "Last generated: 2020-01-01 00:00 UTC" in red.stdout, red.stdout)


def test_a_rendered_model_absent_from_the_store_is_an_obsolete_doc_to_archive():
    """A rendered row for a removed model is an obsolete doc -> archive."""
    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td))
        check("obsolete-row: current rows are green", run(root, "--check").returncode == 0, "")
        text = (root / "README.md").read_text(encoding="utf-8")
        (root / "README.md").write_text(
            text + "|[**Ghost-900B**](https://huggingface.co/x/ghost) | row |\n",
            encoding="utf-8")
        red = run(root, "--check")
    check("obsolete-row: planted row is RED", red.returncode == 1, red.stdout + red.stderr)
    check("obsolete-row: kind=obsolete-doc", "kind=obsolete-doc" in red.stdout, red.stdout)
    check("obsolete-row: action=archive", "action=archive" in red.stdout, red.stdout)
    check("obsolete-row: file=README.md", "file=README.md" in red.stdout, red.stdout)
    check("obsolete-row: exact needle", "[**Ghost-900B**]" in red.stdout, red.stdout)


def test_a_store_model_with_no_row_is_a_false_claim_to_update():
    """A store model the render dropped is a stale render -> update."""
    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td))
        (root / "README.md").write_text(README.replace(
            "|[**Beta**](https://huggingface.co/x/beta) | row |\n", ""), encoding="utf-8")
        red = run(root, "--check")
    check("missing-row: planted drop is RED", red.returncode == 1, red.stdout + red.stderr)
    check("missing-row: kind=false-claim", "kind=false-claim" in red.stdout, red.stdout)
    check("missing-row: action=update", "action=update" in red.stdout, red.stdout)
    check("missing-row: exact needle", "[**Beta**]" in red.stdout, red.stdout)


def test_an_inventory_line_naming_a_deleted_script_is_obsolete():
    """An ARCHITECTURE.md inventory item for a deleted file is obsolete -> archive."""
    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td))
        check("inventory: current tree is green", run(root, "--check").returncode == 0, "")
        (root / "scripts" / "alpha_tool.py").unlink()
        red = run(root, "--check")
    check("inventory: deleted script is RED", red.returncode == 1, red.stdout + red.stderr)
    check("inventory: kind=obsolete-doc", "kind=obsolete-doc" in red.stdout, red.stdout)
    check("inventory: action=archive", "action=archive" in red.stdout, red.stdout)
    check("inventory: file=ARCHITECTURE.md", "file=ARCHITECTURE.md" in red.stdout, red.stdout)
    check("inventory: exact needle", "scripts/alpha_tool.py" in red.stdout, red.stdout)


def test_apply_writes_a_keeper_body_without_mutating_a_doc_or_closing_an_issue():
    """--apply prints a keeper body, closes nothing, and leaves every doc byte-equal."""
    closure = _load(PR_CLOSURE, "pr_closure")
    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td))
        text = (root / "README.md").read_text(encoding="utf-8")
        (root / "README.md").write_text(text + "|[**Ghost**](https://huggingface.co/x/g) | r |\n",
                                        encoding="utf-8")
        before = doc_bytes(root)
        applied = run(root, "--apply")
        after = doc_bytes(root)
        body = applied.stdout
    check("apply: exits 0 on findings", applied.returncode == 0, applied.stdout + applied.stderr)
    check("apply: names the finding", "[**Ghost**]" in body, body[:300])
    check("apply: has an update section", "## False claims to update" in body, body[:300])
    check("apply: has an archive section", "## Obsolete docs to archive" in body, body[:300])
    check("apply: no closing keyword", not closure.closing_bindings(closure.visible_text(body)), body[-300:])
    check("apply: keeper branch closes nothing",
          closure.check(body, "ci/keeper-wiki-maintenance-1773") == [],
          closure.check(body, "ci/keeper-wiki-maintenance-1773"))
    check("apply: every doc is byte-unchanged", before == after,
          f"before={sorted(before)} after={sorted(after)}")


def test_apply_with_no_findings_refuses_loudly():
    """A no-op apply never publishes an empty keeper body (exit 2)."""
    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td))
        applied = run(root, "--apply")
    check("apply: no findings is exit 2", applied.returncode == 2, applied.stdout)
    check("apply: no findings is loud", "no findings" in applied.stderr, applied.stderr)


def test_an_unreadable_tree_is_exit_2_not_a_silent_clean():
    """A missing truth source refuses loudly; it never reports 'no findings'."""
    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td))
        (root / "data" / "models.json").unlink()
        proc = run(root, "--check")
    check("unreadable: exit 2", proc.returncode == 2, proc.stdout + proc.stderr)
    check("unreadable: names the cause", "READ FAILED" in proc.stderr, proc.stderr)


def test_the_seam_is_wired_where_it_bites():
    """Makefile targets, the refresh-bot job, the cron cap and suite discovery."""
    mk = MAKEFILE.read_text(encoding="utf-8")
    wf = WORKFLOW.read_text(encoding="utf-8")
    check("make: internal recipe reaches the checker",
          "python3 scripts/wiki_maintenance.py" in mk, "")
    check("make: wiki-maintenance public wrapper exists",
          re.search(r"(?m)^wiki-maintenance:", mk) is not None, "")
    check("make: wiki-maintenance-check public wrapper exists",
          re.search(r"(?m)^wiki-maintenance-check:", mk) is not None, "")
    check("make: check target reaches the --check seam",
          "--check" in mk[mk.index("wiki-maintenance-check:"):][:400], "")
    check("workflow: refresh-bot carries the wiki-maintenance job",
          re.search(r"(?m)^\s{2}wiki-maintenance:", wf) is not None, "")
    job = wf[wf.index("  wiki-maintenance:"):]
    check("workflow: the job is gated by guard", "needs: guard" in job[:300], job[:300])
    check("workflow: the job runs the check target",
          "make wiki-maintenance-check" in job[:2000], job[:500])
    check("workflow: no new schedule was added",
          len([c for c in re.findall(r'cron:\s*"([^"]+)"', wf)]) == 2, "")
    check("wiring: no other workflow gained a schedule",
          not any(re.search(r"(?m)^\s{2}schedule:\s*$", p.read_text(encoding="utf-8"))
                  for p in (ROOT / ".github" / "workflows").glob("*.yml")
                  if p.name != "refresh-bot.yml"), "")
    check("wiring: this suite is discovered by make test", wired(__file__), "")
    check("module: the checker names both truth files",
          "data/models.json" in mk and
          "generated_utc" in SCRIPT.read_text(encoding="utf-8"), "")


def main() -> int:
    print("wiki_maintenance (issue #1773): offline doc-freshness checker")
    test_a_current_tree_is_green()
    test_a_stale_render_stamp_is_a_false_claim_to_update()
    test_a_rendered_model_absent_from_the_store_is_an_obsolete_doc_to_archive()
    test_a_store_model_with_no_row_is_a_false_claim_to_update()
    test_an_inventory_line_naming_a_deleted_script_is_obsolete()
    test_apply_writes_a_keeper_body_without_mutating_a_doc_or_closing_an_issue()
    test_apply_with_no_findings_refuses_loudly()
    test_an_unreadable_tree_is_exit_2_not_a_silent_clean()
    test_the_seam_is_wired_where_it_bites()
    print(f"{'FAILED' if _FAIL else 'PASSED'} {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
