#!/usr/bin/env python3
"""Behavioural tests for scripts/check_openspec_tasks.py (issue #172).

`openspec validate` checks a change's STRUCTURE but not whether its `- [ ]`
boxes were ticked, so an implementer could leave the checklist unfinished and CI
would stay green. This script is the completion half of the gate; these tests
drive the REAL script (its functions, and the CLI as a subprocess) against
fixture change trees, and assert the repository's own tree is fully ticked.

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

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_openspec_tasks.py"

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
    """The REAL script, imported by path (no copy of its logic in the test)."""
    spec = importlib.util.spec_from_file_location("check_openspec_tasks", SCRIPT)
    assert spec and spec.loader, SCRIPT
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _change(base: Path, name: str, tasks: str, archived: bool = False) -> Path:
    d = (base / "archive" / name) if archived else (base / name)
    d.mkdir(parents=True, exist_ok=True)
    (d / "tasks.md").write_text(tasks, encoding="utf-8")
    return d


def test_unticked_task_fails_and_names_the_line():
    """An active change with a leftover `- [ ]` fails, with the line number."""

    # Given an active change whose checklist is half done
    mod = _module()
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "changes"
        _change(base, "half-done", "# Tasks\n\n- [x] 1. done\n- [ ] 2. not done\n")

        # When  the task gate runs over the active changes
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = mod.check_all(base=base)
        out = buf.getvalue()

    # Then  it fails and names the change and the line of the unticked box
    check("half-done: gate exits non-zero", rc == 1, str(rc))
    check("half-done: the change is named", "half-done" in out, out)
    check("half-done: the unticked line number is named", "[4]" in out, out)


def test_all_ticked_passes():
    """A fully ticked active change passes."""

    # Given an active change with every box ticked
    mod = _module()
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "changes"
        _change(base, "complete", "# Tasks\n\n- [x] 1. done\n- [X] 2. also done\n")

        # When  the gate runs
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = mod.check_all(base=base)

    # Then  it is green
    check("complete: gate exits 0", rc == 0, str(rc) + " " + buf.getvalue())


def test_archived_change_is_ignored():
    """A change under archive/ keeps its task boxes and is not checked."""

    # Given an archived change whose boxes are still unticked
    mod = _module()
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "changes"
        _change(base, "old-and-done", "# Tasks\n\n- [ ] 1. left unticked\n", archived=True)

        # When  the gate runs over the active changes
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = mod.check_all(base=base)
        out = buf.getvalue()

    # Then  it exits 0 and never reports the archived change
    check("archived: gate exits 0", rc == 0, str(rc) + " " + out)
    check("archived: the archived change is not reported", "old-and-done" not in out, out)


def test_checkbox_in_fence_is_not_a_task():
    """A literal `- [ ]` inside a fenced code block is not a task."""

    # Given a change that documents the checkbox syntax inside a fence
    mod = _module()
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "changes"
        _change(
            base,
            "documented",
            "# Tasks\n\n- [x] 1. done\n\n```\n- [ ] this is a sample, not a task\n```\n",
        )

        # When  the gate runs
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = mod.check_all(base=base)

    # Then  the fenced sample does not count as an unticked task
    check("fenced sample: gate exits 0", rc == 0, str(rc) + " " + buf.getvalue())


def test_real_repo_active_changes_are_all_ticked():
    """The repository's own active changes have every task ticked (rule: tick as verified)."""

    # Given this repository's real openspec/changes tree
    mod = _module()

    # When  the gate runs over it (and the CLI runs as CI runs it)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = mod.check_all()
    proc = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, capture_output=True, text=True)

    # Then  it is green both ways
    check("real repo: every active change is fully ticked", rc == 0, buf.getvalue())
    check("real repo: the script's exit code is 0", proc.returncode == 0, proc.stdout + proc.stderr)


def test_wired_into_make_test():
    """The gate is reachable from a make target CI runs (rule 6d)."""

    # Given the Makefile
    mk = (ROOT / "Makefile").read_text()

    # When  the openspec targets are read
    # Then  the task gate is wired, `openspec-check` includes it, and the tests run in the suite
    check("make: openspec-tasks-check runs the script",
          "openspec-tasks-check:" in mk and "python3 scripts/check_openspec_tasks.py" in mk, "")
    check("make: openspec-check runs the task gate",
          "openspec-check: openspec-image openspec-tasks-check openspec-index-check" in mk, "")
    check("make: the task-gate tests run in the suite",
          "python3 tests/test_check_openspec_tasks.py" in mk, "")


def main() -> int:
    print("OpenSpec task gate (scripts/check_openspec_tasks.py)")
    test_unticked_task_fails_and_names_the_line()
    test_all_ticked_passes()
    test_archived_change_is_ignored()
    test_checkbox_in_fence_is_not_a_task()
    test_real_repo_active_changes_are_all_ticked()
    test_wired_into_make_test()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
