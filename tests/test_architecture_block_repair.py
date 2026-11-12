#!/usr/bin/env python3
"""Behavioural tests for scripts/architecture_block_repair.py — the #861 keeper decision.

A merged PR that moved a make target, a script or a workflow job without
`make architecture-refresh` staleness-reds the `push`-to-`master` `validate` run
at `architecture-check` — with no PR-side repairer (rule 6q). Measured 2026-11-12
after merge `91eb093`: the block said '201 make targets, 71 files in scripts/'
while the tree had 201/71+1, and auto-merge of every open PR waited behind a red
whose only named keeper was the Wednesday-only `architecture-bot`. qa-validate's
`architecture-repair` job (the #304 `index-repair` sibling) classifies the drift
against the exact post-merge tree and lands a keeper PR — but ONLY under a
verdict this suite pins.

These tests drive the REAL repair script (imported by path) against fixture
trees shaped like `tests/test_architecture_bot.py`'s — the REAL generator
computes freshness, write and re-check — and the REAL closing parser against the
keeper PR body.

Wired into `make test` (rule 6d).
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import subprocess
import sys
import tempfile
from pathlib import Path

from wiring import wired  # noqa: E402  (issues #176/#192)

ROOT = Path(__file__).resolve().parent.parent
REPAIR_SCRIPT = ROOT / "scripts" / "architecture_block_repair.py"
MAKEFILE = (ROOT / "Makefile").read_text(encoding="utf-8")
WF = ROOT / ".github" / "workflows"

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


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader, path
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ab = _load("architecture_bot_for_repair_tests", ROOT / "scripts" / "architecture_bot.py")
BEGIN, END = ab.BEGIN, ab.END
# The generator's derived FLOW refuses a tree missing any of these; the fixture
# carries the full set so a DRIFT verdict measures BLOCK drift, not a fixture hole.
_FULL = ("search", "merge", "ingest", "validate", "render-readme",
         "test", "refresh", "docker-build", "setup")


def _workflow(targets: tuple[str, ...]) -> str:
    """A workflow whose steps call ONLY these real targets (no decoys)."""
    calls = "".join(f"          make {t}\n" for t in targets)
    return (
        "name: fixture-bot\n\n"
        "on:\n"
        "  schedule:\n"
        '    - cron: "13 5 * * *"\n\n'
        "jobs:\n"
        "  work:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - name: do it\n"
        "        run: |\n"
        + calls
    )


def _tree(td: Path, targets: tuple[str, ...], fresh_block: bool = True) -> Path:
    """A minimal repo whose committed §10 block is current against THIS tree.

    Shaped like `tests/test_architecture_bot.py::_tree` so the real generator
    renders it; `fresh_block=False` commits a block that predates the tree.
    """
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
    (wf / "ci.yml").write_text(_workflow(targets[:1]), encoding="utf-8")
    doc = ("# ARCHITECTURE\n\n## 3. Every `make` target\n\n| Target | What |\n|---|---|\n"
           + "".join(f"| `{t}` | does it |\n" for t in targets)
           + "\n## 4. The pipelines\n\n## 10. The living inventory\n\n"
           + f"{BEGIN}\n" + (ab.render(td) if fresh_block else "stale placeholder") + f"\n{END}\n")
    (td / "ARCHITECTURE.md").write_text(doc, encoding="utf-8")
    return td


def _run(rp, argv: list[str]) -> tuple[int, str]:
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = rp.main(argv)
    return rc, out.getvalue() + err.getvalue()


def _classify(rp, td: Path) -> tuple[int, str]:
    return _run(rp, ["--classify-and-write", "--root", str(td)])


def test_a_stale_block_after_a_merge_classifies_block_only_and_rewrites():
    """The exact post-merge drift: a new script + new target moved the tree, the
    committed block never learned about them -> DRIFT=block-only, ONLY the block
    moves, and the rewrite is current by the generator's own comparison."""
    rp = _load("abr_stale", REPAIR_SCRIPT)
    with tempfile.TemporaryDirectory() as d:
        td = _tree(Path(d), _FULL)
        before = (td / "ARCHITECTURE.md").read_text(encoding="utf-8")
        # the "merge": a new script and a new target land on disk.
        (td / "scripts" / "new_keeper.py").write_text(
            '#!/usr/bin/env python3\n"""The new keeper."""\n', encoding="utf-8")
        mk = (td / "Makefile").read_text(encoding="utf-8")
        (td / "Makefile").write_text(mk + "new-target: ## does the new thing\n\techo new\n",
                                     encoding="utf-8")

        rc, out = _classify(rp, td)
        check("stale block: exit 0", rc == 0, out)
        check("stale block: DRIFT=block-only is printed", "DRIFT=block-only" in out, out)

        after = (td / "ARCHITECTURE.md").read_text(encoding="utf-8")
        check("stale block: only the block moved (prose byte-identical)",
              after.split(BEGIN)[0] == before.split(BEGIN)[0]
              and after.split(END, 1)[1] == before.split(END, 1)[1], "")
        block = ab.block_on_disk(after)
        check("stale block: the rewritten block equals the fresh render",
              block.strip("\n") == ab.render(td).strip("\n"), "")
        # re-running on the repaired tree is a no-op — the keeper is idempotent.
        rc2, out2 = _classify(rp, td)
        check("stale block: a second pass classifies DRIFT=none",
              rc2 == 0 and "DRIFT=none" in out2, out2)


def test_a_current_block_classifies_none_and_writes_nothing():
    """DRIFT=none: the block matches the tree, so the red had another cause; the
    workflow lands nothing and the script must not touch the document."""
    rp = _load("abr_none", REPAIR_SCRIPT)
    with tempfile.TemporaryDirectory() as d:
        td = _tree(Path(d), _FULL)
        before_bytes = (td / "ARCHITECTURE.md").read_bytes()
        rc, out = _classify(rp, td)
        check("current block: exit 0", rc == 0, out)
        check("current block: DRIFT=none is printed", "DRIFT=none" in out, out)
        check("current block: ARCHITECTURE.md bytes untouched",
              (td / "ARCHITECTURE.md").read_bytes() == before_bytes, "")


def test_an_unbacked_tree_refuses_exit_2_and_writes_nothing():
    """A script whose docstring claims `arch-calls: not-a-target` is a DEFECT
    wearing the costume of staleness: the generator itself refuses the tree, so
    exit 2, loud, and the document is byte-untouched — a keeper PR must not
    launder a broken tree with a rewritten block."""
    rp = _load("abr_tree", REPAIR_SCRIPT)
    with tempfile.TemporaryDirectory() as d:
        td = _tree(Path(d), _FULL)
        before_bytes = (td / "ARCHITECTURE.md").read_bytes()
        (td / "scripts" / "claiming.sh").write_text(
            "#!/usr/bin/env bash\n# arch-calls: search not-a-target\necho x\n", encoding="utf-8")
        rc, out = _classify(rp, td)
        check("unbacked tree: exit 2 (never a silent clean, never block-only)",
              rc == 2, out)
        check("unbacked tree: names the generator's own refusal",
              "DRIFT=tree" in out and "not-a-target" in out, out)
        check("unbacked tree: ARCHITECTURE.md bytes untouched",
              (td / "ARCHITECTURE.md").read_bytes() == before_bytes, "")


def test_missing_markers_or_document_exit_2_naming_the_refusal():
    """A document without the generated block (or no document at all) is not
    block drift: restoring it is a human act, and nothing may be written."""
    rp = _load("abr_missing", REPAIR_SCRIPT)
    with tempfile.TemporaryDirectory() as d:
        td = _tree(Path(d), _FULL)
        doc = td / "ARCHITECTURE.md"
        doc.write_text("# ARCHITECTURE\n\nno generated block here at all\n", encoding="utf-8")
        rc, out = _classify(rp, td)
        check("no markers: exit 2", rc == 2, out)
        check("no markers: names the missing BEGIN/END pair", BEGIN in out and END in out, out)

        doc.unlink()
        rc, out = _classify(rp, td)
        check("no document: exit 2", rc == 2, out)
        check("no document: names ARCHITECTURE.md", "ARCHITECTURE.md" in out, out)
        check("no document: nothing was written", not doc.exists(), "")


def test_the_keeper_body_records_drift_and_closes_nothing():
    """The keeper PR body records drift (refs #861) and must not close anything —
    proven with the REAL closing parser against the REAL branch shape."""
    rp = _load("abr_body", REPAIR_SCRIPT)
    rc, body = _run(rp, ["--print-pr-body",
                         "--master-sha", "91eb093f8d5c4a1e9b0f112233445566778899aa",
                         "--run-url", "https://github.com/andyholst/trending-local-llms/actions/runs/1"])
    check("body: exit 0", rc == 0, body)
    check("body: references the tracking issue without closing it",
          "refs #861" in body and "Closes" not in body, body)
    check("body: names the red run it repairs", "actions/runs/1" in body, body)

    pr_closure = _load("pr_closure", ROOT / "scripts" / "pr_closure.py")
    branch = "ci/architecture-block-repair-20261112T120000Z"
    check("body: the real parser sees NO implemented issue on this branch",
          pr_closure.implemented_issue(branch) is None, branch)
    problems = pr_closure.check(body, branch)
    check("body: the real closure gate accepts it", problems == [], problems)

    # the branch shape itself carries no trailing number (rule 6e/#852).
    check("body: branch shape has no issue number",
          pr_closure.implemented_issue(branch) is None, branch)

    rc, out = _run(rp, ["--print-pr-body"])
    check("body: refusing a body with no run to name (exit 2)", rc == 2, out)


def test_the_repair_is_wired_through_make_and_qa_validate():
    """Rule 6m/6d: the script is reachable ONLY through the Makefile, and qa-validate
    calls those targets — a workflow that reaches the script directly, or a target no
    pipeline runs, is the defect this test exists for."""
    check("makefile: architecture-block-repair is a target",
          "\narchitecture-block-repair:" in MAKEFILE, "")
    check("makefile: architecture-block-repair-pr-body is a target",
          "\narchitecture-block-repair-pr-body:" in MAKEFILE, "")
    check("makefile: both .PHONY",
          ".PHONY: architecture-block-repair architecture-block-repair-pr-body" in MAKEFILE, "")

    wf = (WF / "qa-validate.yml").read_text(encoding="utf-8")
    check("qa-validate: calls make architecture-block-repair and propagates its refusal (exit 2)",
          "if ! make architecture-block-repair; then" in wf, "")
    check("qa-validate: composes the body through make architecture-block-repair-pr-body",
          "make architecture-block-repair-pr-body MASTER_SHA=" in wf, "")
    check("qa-validate: never runs the repair script directly (rule 6m)",
          "python3 scripts/architecture_block_repair.py" not in wf, "")


def test_the_suite_is_wired():
    check("wired into `make test` via scripts/run_tests.sh", wired(__file__), "")


def _subprocess_compile():
    proc = subprocess.run([sys.executable, "-m", "py_compile", str(REPAIR_SCRIPT)],
                          capture_output=True, text=True)
    return proc.returncode == 0


def main() -> int:
    assert _subprocess_compile(), "scripts/architecture_block_repair.py does not compile"
    test_a_stale_block_after_a_merge_classifies_block_only_and_rewrites()
    test_a_current_block_classifies_none_and_writes_nothing()
    test_an_unbacked_tree_refuses_exit_2_and_writes_nothing()
    test_missing_markers_or_document_exit_2_naming_the_refusal()
    test_the_keeper_body_records_drift_and_closes_nothing()
    test_the_repair_is_wired_through_make_and_qa_validate()
    test_the_suite_is_wired()
    print(f"[test_architecture_block_repair] {_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
