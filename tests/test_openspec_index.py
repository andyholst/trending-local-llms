#!/usr/bin/env python3
"""Behavioural tests for scripts/openspec_index.py + the root OPENSPEC.md (issue #172).

`OPENSPEC.md` is the ONE file that references every OpenSpec change this repo has
ever had. It is generated, so these tests drive the REAL generator (imported by
path) against a fixture tree that lives under a patched ROOT — a change with no
row must fail the check, a stale row must fail, and the repository's own index
must be current and must list every change directory on disk.

Wired into `make test` (rule 6d).
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from wiring import wired  # noqa: E402  (issues #176/#192)

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "openspec_index.py"

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
    spec = importlib.util.spec_from_file_location("openspec_index", SCRIPT)
    assert spec and spec.loader, SCRIPT
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fixture(td: Path, name: str, tasks: str, issue: str = "", archived: bool = False):
    """A minimal change tree under td, plus the patched module globals."""
    mod = _module()
    setattr(mod, "ROOT", td)
    setattr(mod, "CHANGES", td / "openspec" / "changes")
    setattr(mod, "INDEX", td / "OPENSPEC.md")
    where = (mod.CHANGES / "archive" / name) if archived else (mod.CHANGES / name)
    (where / "specs" / "capability").mkdir(parents=True, exist_ok=True)
    (where / "specs" / "capability" / "spec.md").write_text("# capability\n", encoding="utf-8")
    (where / "tasks.md").write_text(tasks, encoding="utf-8")
    header = f"# Proposal: {name}\n\n" + (f"Issue: {issue}\n\n" if issue else "")
    (where / "proposal.md").write_text(header + "## Why\n\nBecause.\n", encoding="utf-8")
    return mod, where


def _run(mod, argv):
    """main() with stdout/stderr captured (the script prints its verdict there)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = mod.main(argv)
    return rc, out.getvalue() + err.getvalue()


def test_change_with_no_row_fails_the_check():
    """A change on disk that the index does not list fails, and is named."""

    # Given a change directory and an index that predates it
    with tempfile.TemporaryDirectory() as td:
        mod, _ = _fixture(Path(td), "agent-new-thing", "# Tasks\n\n- [x] 1. done\n")
        mod.INDEX.write_text("# OpenSpec index\n\n| Change | State |\n|---|---|\n", encoding="utf-8")

        # When  the index check runs
        rc, out = _run(mod, ["--check"])

    # Then  it fails and names the change with no row
    check("missing row: check exits non-zero", rc == 1, str(rc))
    check("missing row: the change is named", "agent-new-thing" in out, out)


def test_row_carries_issue_specs_and_task_progress():
    """A generated row carries the name, state, issue, spec link and task progress."""

    # Given an active change with an issue ref and a half-done checklist
    with tempfile.TemporaryDirectory() as td:
        mod, _ = _fixture(
            Path(td), "agent-new-thing", "# Tasks\n\n- [x] 1. done\n- [ ] 2. todo\n", issue="#172"
        )

        # When  the index is rendered
        text = mod.render()

    # Then  one row carries everything a reviewer needs
    check("row: the change name is listed", "| `agent-new-thing` |" in text, text)
    check("row: the state is active", "| `agent-new-thing` | active |" in text, text)
    check("row: the issue ref is shown", "| #172 |" in text, text)
    check("row: the capability spec is linked",
          "[capability](openspec/changes/agent-new-thing/specs/capability/spec.md)" in text, text)
    check("row: the task progress is n/m", "| 1/2 |" in text, text)
    check("row: the proposal is linked", "[proposal.md](openspec/changes/agent-new-thing/proposal.md)" in text, text)


def test_archived_change_row_is_marked_archived():
    """An archived change is listed with state `archived`."""

    # Given a change under openspec/changes/archive/
    with tempfile.TemporaryDirectory() as td:
        mod, _ = _fixture(Path(td), "old-thing", "# Tasks\n\n- [x] 1. done\n", archived=True)

        # When  the index is rendered
        text = mod.render()

    # Then  its row says so
    check("archived: the row state is archived", "| `old-thing` | archived |" in text, text)


def test_write_then_check_is_green():
    """`--write` produces exactly what `--check` accepts (generate == verify)."""

    # Given a fixture tree with no index yet
    with tempfile.TemporaryDirectory() as td:
        mod, _ = _fixture(Path(td), "agent-thing", "# Tasks\n\n- [x] 1. done\n")

        # When  it is generated and then checked
        rc_write, _ = _run(mod, ["--write"])
        rc_check, out = _run(mod, ["--check"])

    # Then  both are green (a regenerated index is never stale)
    check("write: exit 0", rc_write == 0, str(rc_write))
    check("check after write: exit 0", rc_check == 0, out)


def test_real_repo_index_is_current_and_lists_every_change():
    """The committed OPENSPEC.md is current and lists every change dir on disk."""

    # Given this repository's real index and change tree
    proc = subprocess.run([sys.executable, str(SCRIPT), "--check"], cwd=ROOT,
                          capture_output=True, text=True)
    text = (ROOT / "OPENSPEC.md").read_text(encoding="utf-8")
    listed = set(re.findall(r"^\| `([^`]+)` \|", text, re.MULTILINE))
    on_disk = {
        p.name
        for p in (ROOT / "openspec" / "changes").iterdir()
        if p.is_dir() and p.name != "archive"
    }

    # When  the rows are compared with the directories
    # Then  the check is green and every change has a row (nothing drifts silently)
    check("real repo: make openspec-index-check exits 0", proc.returncode == 0,
          proc.stdout + proc.stderr)
    check("real repo: every change directory has a row", on_disk <= listed,
          f"on disk={sorted(on_disk)} listed={sorted(listed)}")


def test_a_stale_count_line_is_named_and_not_blamed_on_the_rows():
    """A committed index whose ONLY drift is the count line must say so.

    Measured on `master` 9b3e34c (validate run 38865506979): `OPENSPEC.md` said
    `Active changes: **30**` while the tree held 31 — every row present and
    identical — and the message read `rows exist but their data changed
    (issue/PR/specs/tasks)`, pointing a reader at the rows and at three fields
    that had not moved. A red check must name the cause it actually found.
    """

    # Given a committed index whose ONLY drift is the count line
    with tempfile.TemporaryDirectory() as td:
        mod, _ = _fixture(Path(td), "agent-thing", "# Tasks\n\n- [x] 1. done\n")
        _run(mod, ["--write"])
        good = mod.INDEX.read_text(encoding="utf-8")
        mod.INDEX.write_text(
            re.sub(r"^Active changes: \*\*(\d+)\*\*",
                   lambda m: f"Active changes: **{int(m.group(1)) + 1}**", good, flags=re.MULTILINE),
            encoding="utf-8")

        # When  the check runs
        rc, out = _run(mod, ["--check"])

    # Then  it fails, names the COUNT LINE, and does not blame the rows
    check("count: the check fails", rc != 0, out)
    check("count: the message names the count line", "count line says" in out, out)
    check("count: it does NOT claim the rows changed", "rows whose data changed" not in out, out)


def test_a_row_whose_data_moved_is_named():
    """The other direction: when a row's data really moved, name that row."""

    # Given a change whose tasks.md moved after the index was written
    with tempfile.TemporaryDirectory() as td:
        mod, where = _fixture(Path(td), "agent-thing", "# Tasks\n\n- [x] 1. done\n")
        _run(mod, ["--write"])
        (where / "tasks.md").write_text("# Tasks\n\n- [x] 1. done\n- [ ] 2. new\n", encoding="utf-8")

        # When  the check runs
        rc, out = _run(mod, ["--check"])

    # Then  it fails and names the change whose row moved
    check("row: the check fails", rc != 0, out)
    check("row: the message names the change whose row moved",
          "rows whose data changed" in out and "agent-thing" in out, out)


def test_wired_into_make_test():
    """The generator is reachable from make targets CI runs (rule 6d)."""

    # Given the Makefile
    mk = (ROOT / "Makefile").read_text()

    def recipe(target: str) -> str:
        m = re.search(rf"^{target}:[^\n]*\n((?:\t[^\n]*\n)+)", mk, re.MULTILINE)
        return m.group(1) if m else ""

    # When  the openspec targets are read
    # Then  index + check are wired, `openspec-check` runs the check, and the tests run in the suite
    check("make: openspec-index regenerates the index",
          "--write" in recipe("openspec-index"), recipe("openspec-index"))
    check("make: openspec-index-check verifies it",
          "--check" in recipe("openspec-index-check"), recipe("openspec-index-check"))
    check("make: openspec-check runs the index check",
          "openspec-check: openspec-image openspec-tasks-check openspec-index-check" in mk, "")
    check("make: the index tests run in the suite",
          wired(__file__), "")


def main() -> int:
    print("OpenSpec root index (scripts/openspec_index.py + OPENSPEC.md)")
    test_change_with_no_row_fails_the_check()
    test_row_carries_issue_specs_and_task_progress()
    test_archived_change_row_is_marked_archived()
    test_write_then_check_is_green()
    test_real_repo_index_is_current_and_lists_every_change()
    test_a_stale_count_line_is_named_and_not_blamed_on_the_rows()
    test_a_row_whose_data_moved_is_named()
    test_wired_into_make_test()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
