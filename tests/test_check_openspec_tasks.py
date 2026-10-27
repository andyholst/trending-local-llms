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

from wiring import wired  # noqa: E402  (issues #176/#192)

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


def test_a_blocked_task_is_review_required_not_a_failure():
    """A `- [~] … — blocked: why` box passes the gate and is REPORTED.

    Issue #409: work an agent may not finish (an AGENTS.md row a human must
    apply, a rule-3c signature) had only two exits — tick a box for work that
    was not done, or keep the gate red for ever. The third state is accepted,
    but it must never read as "all tasks checked".
    """

    # Given an active change whose only unfinished task is blocked on a human
    mod = _module()
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "changes"
        _change(
            base,
            "needs-a-signature",
            "# Tasks\n\n- [x] 1. done\n"
            "- [~] 2. AGENTS.md §8 row — blocked: owner approval (rule 3c)\n",
        )

        # When  the gate runs
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = mod.check_all(base=base)
        out = buf.getvalue()

    # Then  it is green, and the blocked task is named as review-required
    check("blocked: gate exits 0", rc == 0, str(rc) + " " + out)
    check("blocked: the change is named REVIEW-REQUIRED", "REVIEW-REQUIRED needs-a-signature" in out, out)
    check("blocked: the blocked line number is named", "[4]" in out, out)
    check("blocked: the summary counts it", "need a HUMAN review" in out, out)


def test_a_blocked_task_is_neither_done_nor_silently_skipped():
    """A blocked box is never reported as a finished checklist.

    The measured defect (issue #409): `- [~]` matched neither state's regex, so
    the line was dropped and the change printed `OK … all tasks checked`.
    """

    # Given a half-finished checklist whose remainder is blocked on a human
    mod = _module()
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "changes"
        _change(
            base,
            "half-blocked",
            "# Tasks\n\n- [x] 1. done\n- [~] 2. waiting — blocked: the owner\n",
        )

        # When  the gate runs over the tree AND over that one change
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_all = mod.check_all(base=base)
        buf1 = io.StringIO()
        with contextlib.redirect_stdout(buf1):
            rc_only = mod.check_all("half-blocked", base=base)
        out, out_only = buf.getvalue(), buf1.getvalue()

    # Then  neither run claims the checklist is complete, and both name it
    check("not done: all-changes run exits 0", rc_all == 0, str(rc_all) + " " + out)
    check("not done: it does NOT say 'all tasks checked'", "all tasks checked" not in out, out)
    check("not done: --only run exits 0", rc_only == 0, str(rc_only) + " " + out_only)
    check("not done: --only does NOT say 'all tasks checked'",
          "all tasks checked" not in out_only, out_only)
    check("not done: --only reports REVIEW-REQUIRED",
          "REVIEW-REQUIRED half-blocked" in out_only, out_only)


def test_a_blocked_task_without_a_reason_fails():
    """A bare `- [~]` with no `blocked:` annotation is a silent skip — refused.

    An unannotated third state would become the very thing the gate exists to
    prevent: an unchecked task wearing a disguise.
    """

    # Given a blocked box that names neither who nor why
    mod = _module()
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "changes"
        _change(base, "vague", "# Tasks\n\n- [x] 1. done\n- [~] 2. something came up\n")

        # When  the gate runs
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = mod.check_all(base=base)
        out = buf.getvalue()

    # Then  it fails and points at the line that needs a reason
    check("unannotated: gate exits non-zero", rc == 1, str(rc) + " " + out)
    check("unannotated: the change is named", "vague" in out, out)
    check("unannotated: the line is named", "[4]" in out, out)
    check("unannotated: the message asks for `blocked:`", "blocked:` reason" in out, out)


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
          wired(__file__), "")
    # issue #409: the gate's own words must not claim every task is ticked when
    # a task is blocked on a human — the report above says otherwise.
    check("make: openspec-check's echo names the review-required blocked state",
          "review-required" in mk, "")
    check("make: the task-check help text describes the blocked state",
          "blocked: <who/why>" in mk, "")


def main() -> int:
    print("OpenSpec task gate (scripts/check_openspec_tasks.py)")
    test_unticked_task_fails_and_names_the_line()
    test_all_ticked_passes()
    test_archived_change_is_ignored()
    test_checkbox_in_fence_is_not_a_task()
    test_a_blocked_task_is_review_required_not_a_failure()
    test_a_blocked_task_is_neither_done_nor_silently_skipped()
    test_a_blocked_task_without_a_reason_fails()
    test_real_repo_active_changes_are_all_ticked()
    test_wired_into_make_test()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
