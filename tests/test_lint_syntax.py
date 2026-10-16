#!/usr/bin/env python3
"""Behavioural tests for scripts/lint_syntax.py (issue #190).

The rule: no tracked Python module raises a `SyntaxWarning` on compile — the
class of defect that let `scripts/update_trending.py` carry an unescaped
backslash in its docstring and warn on every run. These tests drive the REAL
script against a real git fixture (a module with a planted invalid escape, a
clean module, an untracked module) and against this repository, then assert the
wiring — `make lint`, CI, the fix loop and this suite.

Wired into `make test` (rule 6d).
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "lint_syntax.py"

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
    """A real git repo with one clean module and one carrying an invalid escape."""
    root = td
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    (root / "good.py").write_text("y = 1\n", encoding="utf-8")
    # A single backslash + space inside a non-raw string literal — the exact
    # defect of issue #190. Written as raw bytes so the fixture itself is honest.
    (root / "bad.py").write_bytes(b'x = "\\ "\n')
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "fixture")
    return root


def _run(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *args],
                          cwd=ROOT, capture_output=True, text=True)


def test_invalid_escape_is_reported_and_named():
    """A tracked module with an invalid escape sequence fails, and is named."""

    # Given a committed module with a single backslash + space in a string
    with tempfile.TemporaryDirectory() as td:
        root = _fixture(Path(td))

        # When  the lint runs
        proc = _run(root)

    # Then  it exits non-zero, names the module and quotes the warning
    check("invalid escape: exit non-zero", proc.returncode == 1, str(proc.returncode))
    check("invalid escape: the module is named", "bad.py" in proc.stderr, proc.stderr)
    check("invalid escape: the class is named",
          "SyntaxWarning" in proc.stderr and "invalid escape sequence" in proc.stderr, proc.stderr)
    check("invalid escape: the clean module is NOT named", "good.py" not in proc.stderr, proc.stderr)


def test_clean_tree_is_green():
    """A tree whose modules all compile cleanly is green."""

    # Given a committed module with no invalid escape
    with tempfile.TemporaryDirectory() as td:
        root = _fixture(Path(td))
        (root / "bad.py").write_text("x = '\\\\ '\n", encoding="utf-8")  # a raw-safe literal
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", "fix")

        # When  the lint runs
        proc = _run(root)

    # Then  it exits 0 and reports the count
    check("clean: exit 0", proc.returncode == 0, proc.stderr + proc.stdout)
    check("clean: reports every module", "OK every one of" in proc.stdout, proc.stdout)


def test_untracked_module_is_not_a_finding():
    """An untracked module cannot fail the lint (the file set is what git tracks)."""

    # Given an untracked module with an invalid escape
    with tempfile.TemporaryDirectory() as td:
        root = _fixture(Path(td))
        _git(root, "rm", "--cached", "-q", "bad.py")
        (root / "scratch.py").write_bytes(b'z = "\\ "\n')

        # When  the lint runs
        proc = _run(root)

    # Then  it is green and the untracked module is ignored
    check("untracked: exit 0", proc.returncode == 0, proc.stderr + proc.stdout)
    check("untracked: not named", "scratch.py" not in proc.stderr, proc.stderr)


def test_real_repo_has_no_syntax_warnings():
    """This repository's own tracked modules all compile without a SyntaxWarning.

    This is the regression lock for issue #190: the module that warned must never
    warn again, and no future module may join it.
    """

    # Given the real checkout
    proc = _run(ROOT)

    # When  the lint runs on it
    # Then  it is green (the gate is green on the tree it ships)
    check("real repo: make lint-syntax is green", proc.returncode == 0, proc.stdout + proc.stderr)


def test_wired_into_make_ci_the_loop_and_the_suite():
    """`make lint` runs the guard, and CI, the fix loop and the suite carry it (rule 6d)."""

    # Given the Makefile, the PR pipeline and the fix loop
    mk = (ROOT / "Makefile").read_text()
    qa = (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text()
    loop = (ROOT / "scripts" / "fix_loop.sh").read_text()

    # When  their wiring is read
    # Then  the guard runs in `lint`, and the gate is where the rules require
    check("make: the lint target runs the guard",
          "lint:" in mk and "python3 scripts/lint_syntax.py" in mk, "")
    check("ci: qa-validate runs make lint", "make lint" in qa, "")
    check("loop: lint is the first check",
          loop.split("CHECKS=(", 1)[1].split(")", 1)[0].strip().startswith("lint"),
          loop.split("CHECKS=(", 1)[1][:60])
    check("make: these tests run in the suite", "python3 tests/test_lint_syntax.py" in mk, "")


def main() -> int:
    print("syntax-warning lint (scripts/lint_syntax.py, issue #190)")
    test_invalid_escape_is_reported_and_named()
    test_clean_tree_is_green()
    test_untracked_module_is_not_a_finding()
    test_real_repo_has_no_syntax_warnings()
    test_wired_into_make_ci_the_loop_and_the_suite()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
