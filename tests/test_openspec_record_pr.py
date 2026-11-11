#!/usr/bin/env python3
"""The completing PR's number is RECORDED on the change it completes AND the change is
ARCHIVED, in the PR that completes it (issue #518).

Rule 6f gives every change a life that ENDS in the PR completing it: once its
`PR:` line is known, that PR writes `PR: #<n>` AND moves the change to
`openspec/changes/archive/`, then regenerates the index. The gap measured on
`master`: `scripts/openspec_archive_check.py` could only see a change that
CARRIED a `PR:` line, and 110 of 111 active changes had none — a merged-and-
forgotten change was invisible, so the guard's "none names a PR" was vacuous.

The recording/archiving half belongs to the WORKFLOW that opens the PR: once
`gh pr create` has returned a number, `make openspec-record-pr ISSUE=<n> PR=<m>`
(`scripts/openspec_record_pr.py`) writes `PR: #<m>` into every ACTIVE change
whose proposal references `Issue: #<n>` — found through the SHARED
`openspec_index._refs` parser (rule 6d, one reader) — moves those changes to
`archive/`, and regenerates `OPENSPEC.md`. Nothing is fabricated: the script
only copies a number the workflow already knows, and it REFUSES (exit 2) when no
active change names the issue, so a recording that silently matched nothing
could never leave the guard vacuous again.

These tests drive the REAL script against a REAL fixture tree (no GitHub — the
script needs no external system), and the shipped workflow step end to end to
prove the recording is wired after the PR opens.

Wired into `make test` (rule 6d).
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

from wiring import wired  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "openspec_record_pr.py"
MAKEFILE = ROOT / "Makefile"
ISSUE_BOT = ROOT / ".github" / "workflows" / "issue-bot.yml"

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


def _tree(td: Path, name: str, issue: str, existing_pr: str = "") -> Path:
    """A real active-change dir whose proposal references `issue`."""
    change = td / "openspec" / "changes" / name
    (change / "specs" / "capability").mkdir(parents=True, exist_ok=True)
    (change / "specs" / "capability" / "spec.md").write_text("# capability\n", encoding="utf-8")
    (change / "tasks.md").write_text("# Tasks\n\n- [x] 1. done\n", encoding="utf-8")
    pr_line = f"\n{existing_pr}" if existing_pr else ""
    (change / "proposal.md").write_text(
        f"# Proposal: {name}\n\nIssue: {issue}{pr_line}\n\n## Why\n\nBecause.\n",
        encoding="utf-8",
    )
    return change


def _run(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *args],
        capture_output=True, text=True,
    )


def test_the_recording_writes_the_pr_line_archives_and_regenerates_the_index():
    """`openspec-record-pr` writes the PR line, moves the change to archive/, updates the index."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _tree(root, "my-change", "#518")

        rc = _run(root, "--issue", "518", "--pr", "523")

        archived = root / "openspec" / "changes" / "archive" / "my-change" / "proposal.md"
        active = root / "openspec" / "changes" / "my-change" / "proposal.md"
        index = (root / "OPENSPEC.md").read_text(encoding="utf-8")
        check("record-pr: exit 0", rc.returncode == 0, rc.stderr)
        check("record-pr: the change is ARCHIVED (removed from active)",
              not active.exists() and archived.exists(), str(active))
        text = archived.read_text(encoding="utf-8")
        check("record-pr: the archived proposal carries PR: #523", "PR: #523" in text, text)
        check("record-pr: the index lists it as archived",
              "my-change` | archived |" in index, index[:400])
        check("record-pr: it reports which change it touched", "my-change" in rc.stdout, rc.stdout)


def test_record_refuses_when_no_change_names_the_issue():
    """A recording that matched nothing is LOUD (exit 2), never a vacuous success."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _tree(root, "some-change", "#7")  # a DIFFERENT issue

        rc = _run(root, "--issue", "518", "--pr", "523")

    check("record-pr: no matching change exits 2", rc.returncode == 2, str(rc.returncode))
    check("record-pr: the refusal names the issue", "#518" in rc.stderr, rc.stderr)


def test_record_replaces_an_existing_pr_line():
    """An existing `PR:` line is replaced in place, never duplicated."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _tree(root, "my-change", "#518", existing_pr="PR: #1")

        _run(root, "--issue", "518", "--pr", "523")

        text = (root / "openspec" / "changes" / "archive" / "my-change" / "proposal.md").read_text(encoding="utf-8")
        check("record-pr: carries exactly ONE PR line", text.count("PR: #") == 1, text)
        check("record-pr: it is the NEW number", "PR: #523" in text, text)


def test_the_issue_bot_step_records_the_pr_after_opening_it():
    """The shipped issue-bot workflow runs `make openspec-record-pr` after the PR opens."""
    wf = yaml.safe_load(ISSUE_BOT.read_text(encoding="utf-8"))
    hay = "\n".join(str(s) for s in wf["jobs"]["implement"]["steps"])
    check("record-pr: workflow has an Open the PR step", "Open the PR" in hay, hay[-300:])
    check("record-pr: workflow records the PR through the target", "make openspec-record-pr" in hay, "")


def test_the_guard_target_is_wired():
    mk = MAKEFILE.read_text(encoding="utf-8")
    check("makefile: the recording target exists", "\nopenspec-record-pr:" in mk, "")
    check("makefile: it runs the script", "scripts/openspec_record_pr.py" in mk, "")
    check("tests: this module is run by the suite", wired(__file__), "")


def main() -> int:
    for fn in (
        test_the_recording_writes_the_pr_line_archives_and_regenerates_the_index,
        test_record_refuses_when_no_change_names_the_issue,
        test_record_replaces_an_existing_pr_line,
        test_the_issue_bot_step_records_the_pr_after_opening_it,
        test_the_guard_target_is_wired,
    ):
        print(f"-- {fn.__name__}")
        fn()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
