#!/usr/bin/env python3
"""Behavioural tests for scripts/lint_linefeeds.py (issue #186).

The rule: every tracked text file ends with exactly one final newline, `make lint`
fails closed when one does not, and `make lint-fix` repairs it. These tests drive
the REAL script against a real git fixture (a tracked file it can strip, a binary
file, an empty file, a nested file) and against this repository, then assert the
wiring — CI, the fix loop and this suite.

Wired into `make test` (rule 6d).
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "lint_linefeeds.py"

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


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _fixture(td: Path) -> Path:
    """A real git repo with one good file, one nested, one binary, one empty."""
    root = td
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    (root / "good.txt").write_text("has a newline\n", encoding="utf-8")
    (root / "empty.txt").write_bytes(b"")
    (root / "nested").mkdir(parents=True, exist_ok=True)
    (root / "nested" / "deep.md").write_text("# fine\n", encoding="utf-8")
    (root / "blob.bin").write_bytes(b"\x00\x01\x02binary")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "fixture")
    return root


def _run(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *args],
                          cwd=ROOT, capture_output=True, text=True)


def test_missing_newline_is_reported_and_named():
    """A tracked text file without a final newline fails, and is named."""

    # Given a committed file whose final newline was stripped
    with tempfile.TemporaryDirectory() as td:
        root = _fixture(Path(td))
        (root / "good.txt").write_bytes(b"no trailing newline")

        # When  the lint runs
        proc = _run(root)

    # Then  it exits non-zero and names the file with the repair command
    check("missing newline: exit non-zero", proc.returncode == 1, str(proc.returncode))
    check("missing newline: the file is named", "good.txt" in proc.stderr, proc.stderr)
    check("missing newline: the fix is suggested", "make lint-fix" in proc.stderr, proc.stderr)


def test_fix_appends_one_newline_and_is_idempotent():
    """`--fix` appends exactly one newline, and a second run changes nothing."""

    # Given one file missing its newline and one that already has it
    with tempfile.TemporaryDirectory() as td:
        root = _fixture(Path(td))
        (root / "good.txt").write_bytes(b"text without newline")
        before = (root / "nested" / "deep.md").read_bytes()

        # When  the fix runs twice
        first = _run(root, "--fix")
        first_bytes = (root / "good.txt").read_bytes()
        after_fine = (root / "nested" / "deep.md").read_bytes()
        second = _run(root, "--fix")
        after = _run(root)

    # Then  the file ends with exactly one newline, an untouched file is unchanged,
    #       and the second run is a no-op that still exits 0
    check("fix: exit 0", first.returncode == 0, first.stderr)
    check("fix: exactly one newline appended", first_bytes == b"text without newline\n", str(first_bytes))
    check("fix: a file that was already fine is untouched", after_fine == before, str(after_fine))
    check("fix: idempotent (second run exit 0)", second.returncode == 0, second.stderr)
    check("fix: idempotent (nothing left to repair)", "0 repaired" in second.stdout, second.stdout)
    check("lint after fix: exit 0", after.returncode == 0, after.stderr + after.stdout)


def test_binary_and_empty_files_are_not_findings():
    """A binary file and an empty file are not 'missing a newline'."""

    # Given a committed binary file with no trailing newline and an empty file
    with tempfile.TemporaryDirectory() as td:
        root = _fixture(Path(td))

        # When  the lint runs (the fixture also has a stripped text file)
        (root / "good.txt").write_bytes(b"stripped")
        proc = _run(root)

    # Then  only the text file is reported
    check("binary: not reported", "blob.bin" not in proc.stderr, proc.stderr)
    check("empty: not reported", "empty.txt" not in proc.stderr, proc.stderr)
    check("binary/empty: the text file IS reported", "good.txt" in proc.stderr, proc.stderr)


def test_crlf_only_file_is_reported():
    """A file ending in CRLF (no bare LF) is still reported: the last byte is not a newline."""

    # Given a file whose final byte is CR
    with tempfile.TemporaryDirectory() as td:
        root = _fixture(Path(td))
        (root / "good.txt").write_bytes(b"line one\r\nline two\r")

        # When  the lint runs
        proc = _run(root)

    # Then  it is reported
    check("crlf: reported", proc.returncode == 1 and "good.txt" in proc.stderr, proc.stderr)


def test_untracked_file_is_not_a_finding():
    """An untracked file cannot fail the lint (the file set is what git tracks)."""

    # Given an untracked file without a newline
    with tempfile.TemporaryDirectory() as td:
        root = _fixture(Path(td))
        (root / "scratch.md").write_bytes(b"not tracked")

        # When  the lint runs
        proc = _run(root)

    # Then  it is green and the untracked file is ignored
    check("untracked: exit 0", proc.returncode == 0, proc.stderr + proc.stdout)
    check("untracked: not named", "scratch.md" not in proc.stderr, proc.stderr)


def test_real_repo_ends_with_newlines():
    """This repository's own tracked files all end with a newline."""

    # Given the real checkout
    proc = _run(ROOT)

    # When  the lint runs on it
    # Then  it is green (the gate is green on the tree it ships)
    check("real repo: make lint is green", proc.returncode == 0, proc.stdout + proc.stderr)


def test_wired_into_make_ci_the_loop_and_the_suite():
    """`lint` is a make target, a CI step, a fix-loop check and a suite member (rule 6d)."""

    # Given the Makefile, the PR pipeline and the fix loop
    mk = (ROOT / "Makefile").read_text()
    qa = (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text()
    loop = (ROOT / "scripts" / "fix_loop.sh").read_text()

    # When  their wiring is read
    # Then  both targets exist, CI and the loop run the gate, and the suite carries these tests
    check("make: the lint target runs the script",
          "lint:" in mk and "python3 scripts/lint_linefeeds.py" in mk, "")
    check("make: the lint-fix target repairs", "lint-fix:" in mk and "--fix" in mk, "")
    check("ci: qa-validate runs make lint", "make lint" in qa, "")
    check("loop: lint is the first check", loop.split("CHECKS=(", 1)[1].split(")", 1)[0].strip().startswith("lint"),
          loop.split("CHECKS=(", 1)[1][:60])
    check("make: these tests run in the suite", "python3 tests/test_lint_linefeeds.py" in mk, "")
    check("editorconfig: the editor half of the rule is present",
          (ROOT / ".editorconfig").is_file()
          and "insert_final_newline = true" in (ROOT / ".editorconfig").read_text(), "")


def main() -> int:
    print("trailing-newline lint (scripts/lint_linefeeds.py, issue #186)")
    test_missing_newline_is_reported_and_named()
    test_fix_appends_one_newline_and_is_idempotent()
    test_binary_and_empty_files_are_not_findings()
    test_crlf_only_file_is_reported()
    test_untracked_file_is_not_a_finding()
    test_real_repo_ends_with_newlines()
    test_wired_into_make_ci_the_loop_and_the_suite()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
