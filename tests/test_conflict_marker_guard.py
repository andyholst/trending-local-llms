#!/usr/bin/env python3
"""A conflict marker never reaches a commit (issue #588).

`#583` removed the one PRODUCER of markers it knew about — a conflicted `branch-adopt` re-apply
— but the commit step of both bots is `git add -A`, so a marker left by ANY other source (a
botched manual merge, a salvaged detached run, an operator's `git stash pop`) is committed and
the next `make` dies parsing its own Makefile: measured on run 40202490846,
`Makefile:588: *** missing separator`, with no repair possible afterwards.

These tests run the REAL `scripts/check_conflict_markers.py` against real git repositories, and
read the REAL workflow text, so what is proved is what the bots run.

Run:  python3 tests/test_conflict_marker_guard.py    or   make test
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_conflict_markers.py"

_PASS = 0
_FAIL = 0


def check(name, cond, detail=None):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        shown = "" if detail is None or detail == "" else f"  [{detail}]"
        print(f"  FAIL {name}{shown}")


def git(args, cwd):
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)


def repo(td: Path) -> Path:
    d = td / "repo"
    d.mkdir(parents=True)
    git(["init", "-q", "-b", "master"], d)
    git(["config", "user.email", "t@example.com"], d)
    git(["config", "user.name", "t"], d)
    (d / ".gitignore").write_text("scratch\n")
    (d / "clean.py").write_text("print(1)\n")
    git(["add", "-A"], d)
    git(["commit", "-qm", "base"], d)
    return d


def run(d: Path, *extra: str):
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(d), *extra],
                          capture_output=True, text=True)


# The markers are BUILT, never written literally: this file is tracked, and the guard under test
# scans every tracked file — a literal marker here would make the guard fail on its own fixture
# (measured on PR #589's first validate run, which flagged lines 63/65/67 of this file).
_M = {"ours": "<" * 7, "sep": "=" * 7, "base3": "|" * 7, "theirs": ">" * 7}
MARKED = (f"base\n{_M['ours']} HEAD\nours()\n{_M['sep']}\ntheirs()\n"
          f"{_M['theirs']} ci/data-gap-1-x\nend\n")


def test_a_marked_tracked_file_is_refused():
    with tempfile.TemporaryDirectory() as td:
        d = repo(Path(td))
        (d / "Makefile").write_text(MARKED)
        git(["add", "-A"], d)
        git(["commit", "-qm", "carries markers"], d)
        p = run(d)
        check("markers: a committed conflict block exits non-zero", p.returncode == 1, p.returncode)
        check("markers: it NAMES the path", "Makefile" in p.stderr, p.stderr)
        check("markers: it names the line", "line(s) 2" in p.stderr, p.stderr)
        check("markers: it explains why it matters (a parsed file breaks every make)",
              "make" in p.stderr.lower(), p.stderr)


def test_a_clean_tree_passes():
    with tempfile.TemporaryDirectory() as td:
        d = repo(Path(td))
        p = run(d)
        check("markers: a clean repository exits 0", p.returncode == 0, (p.returncode, p.stderr))
        check("markers: it says what it scanned", "OK:" in p.stdout, p.stdout)


def test_an_ignored_or_untracked_file_does_not_fail():
    with tempfile.TemporaryDirectory() as td:
        d = repo(Path(td))
        (d / "scratch").write_text(MARKED)          # ignored by .gitignore
        (d / "draft.txt").write_text(MARKED)        # untracked
        p = run(d)
        check("markers: an ignored/untracked scratch file is not a finding",
              p.returncode == 0, (p.returncode, p.stderr))


def test_a_binary_file_is_not_scanned():
    with tempfile.TemporaryDirectory() as td:
        d = repo(Path(td))
        (d / "icon.bin").write_bytes(b"\x89PNG\r\n\x1a\n\0<<<<<<< HEAD\n=======\n")
        git(["add", "-A"], d)
        git(["commit", "-qm", "binary"], d)
        p = run(d)
        check("markers: a NUL byte in the head means binary, and is skipped",
              p.returncode == 0, (p.returncode, p.stderr))


def test_every_git_marker_shape_is_caught():
    with tempfile.TemporaryDirectory() as td:
        d = repo(Path(td))
        for name, text in (
                ("diff3.txt", f"a\n{_M['base3']} base\nb\n{_M['sep']}\nc\n{_M['theirs']} x\n"),
                ("sep.txt", f"a\n{_M['sep']}\nb\n"),
                ("ours.txt", f"a\n{_M['ours']} HEAD\nb\n")):
            (d / name).write_text(text)
        git(["add", "-A"], d)
        git(["commit", "-qm", "shapes"], d)
        p = run(d)
        check("markers: `<<<<<<<`, `=======`, `|||||||` and `>>>>>>>` all count",
              p.returncode == 1 and all(n in p.stderr for n in ("diff3.txt", "sep.txt", "ours.txt")),
              p.stderr)


def test_six_equals_is_not_a_marker():
    """Only the 7-character run is git's marker; `======` is a legitimate markdown rule."""
    with tempfile.TemporaryDirectory() as td:
        d = repo(Path(td))
        (d / "doc.md").write_text("title\n\n======\n\nbody\n")
        git(["add", "-A"], d)
        git(["commit", "-qm", "rule"], d)
        p = run(d)
        check("markers: a 6-character rule is not a conflict block", p.returncode == 0,
              (p.returncode, p.stderr))


def test_the_bots_and_lint_run_the_guard():
    """Rule 6d/6m: the guard must be wired where it bites, or it proves nothing."""
    ib = (ROOT / ".github/workflows/issue-bot.yml").read_text()
    fb = (ROOT / ".github/workflows/fix-bot.yml").read_text()
    for name, text in (("issue-bot", ib), ("fix-bot", fb)):
        idx = text.find("make check-conflict-markers")
        add = text.find("git add -A", idx)
        check(f"{name}: the commit step runs the guard", idx != -1, "")
        check(f"{name}: it runs BEFORE `git add -A` (a marker must stop the commit)",
              idx != -1 and add > idx, (idx, add))
    # The adopt switches the tree to the BRANCH (a stale branch drops files master added), so
    # the guard must run on THIS RUN's tree, before the adopt — measured on run 40210081952.
    check("issue-bot: the guard runs BEFORE the branch is adopted",
          ib.find("make check-conflict-markers") < ib.find("make branch-adopt"), "")
    makefile = (ROOT / "Makefile").read_text()
    check("makefile: `lint` runs the guard", "check-conflict-markers" in makefile.split("lint:")[1][:600], "")
    check("makefile: the target exists",
          "\ncheck-conflict-markers:" in makefile, "")


def main() -> int:
    print("conflict-marker guard: unit tests")
    test_a_marked_tracked_file_is_refused()
    test_a_clean_tree_passes()
    test_an_ignored_or_untracked_file_does_not_fail()
    test_a_binary_file_is_not_scanned()
    test_every_git_marker_shape_is_caught()
    test_six_equals_is_not_a_marker()
    test_the_bots_and_lint_run_the_guard()
    print(f"PASSED {_PASS} | FAILED {_FAIL}")
    return 0 if _FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
