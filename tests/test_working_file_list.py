#!/usr/bin/env python3
"""The bot's working files live in ONE list (issue #543).

The unstage-before-commit line used to be a long literal, copied verbatim into two steps of
`issue-bot.yml`, a third time into `fix-bot.yml`, and a fourth time into `.gitignore`. Adding a
working file meant remembering all four; a miss meant the push step's `git add -A` committed it
— measured with `qa-report.txt.notes`, a 0-byte scratch note that reached PR #387 (issue #390).

Now `scripts/issue_bot_working_files.txt` is the list, `make reset-working-files` unstages it,
and `make check-working-files` proves every name on it is also gitignored. These tests run the
REAL script against real git repositories.

Run:  python3 tests/test_working_file_list.py    or   make test
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "reset_working_files.py"
LIST = ROOT / "scripts" / "issue_bot_working_files.txt"

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


def repo(td: Path, ignore: str) -> Path:
    d = td / "repo"
    (d / "scripts").mkdir(parents=True)
    git(["init", "-q", "-b", "master"], d)
    git(["config", "user.email", "t@example.com"], d)
    git(["config", "user.name", "t"], d)
    (d / ".gitignore").write_text(ignore)
    (d / "scripts" / "issue_bot_working_files.txt").write_text("issue.md\nfindings.md\n")
    (d / "real.txt").write_text("base\n")
    git(["add", "-A"], d)
    git(["commit", "-qm", "base"], d)
    return d


def run(root: Path, *extra: str):
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *extra],
                          capture_output=True, text=True)


def test_it_unstages_the_list_and_keeps_the_real_change():
    with tempfile.TemporaryDirectory() as td:
        d = repo(Path(td), ignore="issue.md\nfindings.md\n")
        for name in ("issue.md", "findings.md", "real.txt"):
            (d / name).write_text(f"{name} changed\n")
        git(["add", "-f", "issue.md", "findings.md", "real.txt"], d)
        proc = run(d)
        staged = git(["diff", "--cached", "--name-only"], d).stdout.split()
        check("reset: it succeeds", proc.returncode == 0, (proc.returncode, proc.stderr))
        check("reset: the listed scratch is unstaged",
              "issue.md" not in staged and "findings.md" not in staged, staged)
        check("reset: the real change stays staged", "real.txt" in staged, staged)
        check("reset: the scratch is still on disk (only unstaged)",
              (d / "issue.md").exists(), "")
        check("reset: it names what it unstaged", "issue.md" in proc.stdout, proc.stdout)


def test_check_fails_when_a_name_is_not_gitignored():
    with tempfile.TemporaryDirectory() as td:
        d = repo(Path(td), ignore="issue.md\n")          # findings.md is NOT ignored
        proc = run(d, "--check")
        check("check: an un-ignored name fails the guard", proc.returncode == 1, proc.returncode)
        check("check: it names the name", "findings.md" in proc.stderr, proc.stderr)


def test_check_refuses_a_missing_or_empty_list():
    with tempfile.TemporaryDirectory() as td:
        d = repo(Path(td), ignore="issue.md\nfindings.md\n")
        (d / "scripts" / "issue_bot_working_files.txt").write_text("# only comments\n")
        proc = run(d, "--check")
        check("check: an empty list is a vacuous guard and fails",
              proc.returncode == 1 and "vacuous" in proc.stderr, (proc.returncode, proc.stderr))
        (d / "scripts" / "issue_bot_working_files.txt").unlink()
        proc = run(d, "--check")
        check("check: a missing list fails loudly", proc.returncode == 1, proc.returncode)


def test_a_broken_git_tree_is_not_a_pass():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "not-a-repo"
        d.mkdir()
        proc = run(d, "--check")
        check("check: a directory that is not a git checkout fails",
              proc.returncode == 1 and "not a git checkout" in proc.stderr, proc.stderr)


def test_this_repository_passes():
    # A worktree's `.git` is a FILE pointing at the main clone, which is outside the container's
    # mount — git cannot read it there. Say so instead of reporting a pass that never ran; CI
    # (a real clone) executes the check.
    if subprocess.run(["git", "rev-parse", "--git-dir"], cwd=str(ROOT),
                      capture_output=True).returncode != 0:
        print("  ..  this repo: skipped — the checkout's .git is outside the mount "
              "(CI runs it in a real clone)")
        return
    proc = run(ROOT, "--check")
    check("this repo: every working file is gitignored", proc.returncode == 0,
          (proc.returncode, proc.stderr))
    names = [l.strip() for l in LIST.read_text().splitlines()
             if l.strip() and not l.strip().startswith("#")]
    check("this repo: the list is not vacuous", len(names) >= 8, names)
    check("this repo: the capture classes are on it",
          {"implement.log", "issue.md", "findings.md", "pr-body.md"} <= set(names), names)


def test_one_list_one_target():
    """Rule 6d/6m: the list is only a definition if the bots actually call the target."""
    wf = "\n".join(p.read_text() for p in sorted((ROOT / ".github" / "workflows").glob("*.yml")))
    check("wiring: no workflow carries the literal reset line any more",
          "git reset -q -- qa-report.txt" not in wf, "")
    check("wiring: three call sites (issue-bot x2, fix-bot x1) use the target",
          wf.count("make reset-working-files") == 3, wf.count("make reset-working-files"))
    makefile = (ROOT / "Makefile").read_text()
    check("wiring: the Makefile defines the target", "\nreset-working-files:" in makefile, "")
    check("wiring: `lint` runs the check",
          "check-working-files" in makefile.split("lint:")[1][:700], "")


def main() -> int:
    print("working-file list: unit tests")
    test_it_unstages_the_list_and_keeps_the_real_change()
    test_check_fails_when_a_name_is_not_gitignored()
    test_check_refuses_a_missing_or_empty_list()
    test_a_broken_git_tree_is_not_a_pass()
    test_this_repository_passes()
    test_one_list_one_target()
    print(f"PASSED {_PASS} | FAILED {_FAIL}")
    return 0 if _FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
