#!/usr/bin/env python3
"""Two sibling implementation PRs must NOT collide on the analysis seam (issue #1493).

The measured defect: ONE tracked root `findings.md` was the shared append point —
every implementation run appended its own `## <title>` section, so any two open PRs
answered `CONFLICT (content): Merge conflict in findings.md`, GitHub built no merge
commit, and `auto-merge` refused them both (PR #1488 took three rebase rounds to land
a test-only change). The seam is now PER ISSUE (`findings/<issue>.md`) and the root
file is no longer tracked.

These tests drive the REAL resolver (`scripts/file_findings.py::analysis_path` /
`main`) and REAL git: a scratch repository whose two sibling branches touch DIFFERENT
issues merges cleanly in both orders, while the OLD shape — both branches appending one
root `findings.md` — conflicts, so this guard can see the defect it prevents rather than
asserting a property of a fixture.

Run:  python3 tests/test_findings_seam.py    or   make test
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
SCRIPT = ROOT / "scripts" / "file_findings.py"

_PASS = 0
_FAIL = 0


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        shown = "" if not detail else f"  [{detail}]"
        print(f"  FAIL {name}{shown}")


def _module():
    spec = importlib.util.spec_from_file_location("file_findings", SCRIPT)
    assert spec and spec.loader, SCRIPT
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git(args, cwd):
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)


def _tracked() -> subprocess.CompletedProcess:
    """The tracked paths of THIS checkout.

    `make test` runs in a container as root over a host-owned bind mount, where git's
    ownership guard refuses the repository; a read-only `safe.directory` override keeps
    this query honest in both the host and container identities. Without it the "root
    file is absent" assertion would pass VACUOUSLY on an unreadable index (measured on
    PR #1592's first CI run).
    """
    return git(["-c", "safe.directory=*", "ls-files"], ROOT)


def _seed_repo(td: Path, *, track_root: bool) -> Path:
    """A scratch repository at `td/repo` with one base commit.

    `track_root=True` seeds the PRE-#1493 world (a tracked root `findings.md`); the
    default seeds the post-#1493 world (no root file, a `findings/` directory).
    """
    d = td / "repo"
    d.mkdir(parents=True)
    git(["init", "-q", "-b", "master"], d)
    git(["config", "user.email", "t@example.com"], d)
    git(["config", "user.name", "t"], d)
    if track_root:
        (d / "findings.md").write_text("# Findings\n", encoding="utf-8")
    else:
        (d / "findings").mkdir()
        (d / "findings" / "history.md").write_text("# Findings (historical)\n", encoding="utf-8")
    (d / "work.txt").write_text("base\n", encoding="utf-8")
    git(["add", "-A"], d)
    git(["commit", "-qm", "base"], d)
    return d


def _sibling(d: Path, name: str, *, root: bool, issue: str, title: str) -> None:
    """One sibling branch: append to the root file, or create the per-issue file."""
    git(["checkout", "-q", "-b", name, "master"], d)
    if root:
        path = d / "findings.md"
        path.write_text(path.read_text(encoding="utf-8")
                        + f"\n## {title}\n\n- **Evidence:** {name}\n- **Why:** w\n- **Done when:** d\n",
                        encoding="utf-8")
    else:
        (d / "findings" / f"{issue}.md").write_text(
            f"# Findings — #{issue}\n\n## {title}\n\n"
            f"- **Evidence:** {name}\n- **Why:** w\n- **Done when:** d\n", encoding="utf-8")
    git(["add", "-A"], d)
    git(["commit", "-qm", name], d)


def _merge(d: Path, branch: str) -> subprocess.CompletedProcess:
    return git(["merge", "--no-edit", branch], d)


def test_each_issue_resolves_to_its_own_file():
    """The ONE resolver maps an issue (or its branch) to a file no sibling shares."""
    with tempfile.TemporaryDirectory() as td:
        mod = _module()
        setattr(mod, "FINDINGS_DIR", Path(td) / "findings")   # isolate from the real tree
        a = mod.analysis_path(issue="1001")
        b = mod.analysis_path(issue="1002")

        check("resolver: two issues are two files", a != b, f"{a} vs {b}")
        check("resolver: the file is named for its issue",
              a.name == "1001.md" and b.name == "1002.md", f"{a.name}, {b.name}")
        check("resolver: a branch encodes the same issue as --issue",
              mod.analysis_path(branch="ci/data-gap-1001-storage-x") == a
              and mod.analysis_path(branch="fix/findings-seam-per-issue-1493").name == "1493.md",
              "")
        check("resolver: an explicit --path always wins",
              mod.analysis_path(path=str(Path(td) / "x.md"), issue="1001").name == "x.md", "")
        check("resolver: no issue and no branch falls back to the legacy root",
              mod.analysis_path() == mod.LEGACY_FINDINGS, str(mod.LEGACY_FINDINGS))


def test_the_real_cli_checks_the_per_issue_file():
    """`--check --issue N` reads findings/N.md (and a branch encodes the same N)."""
    with tempfile.TemporaryDirectory() as td:
        mod = _module()
        setattr(mod, "FINDINGS_DIR", Path(td) / "findings")
        mod.FINDINGS_DIR.mkdir(parents=True)
        (mod.FINDINGS_DIR / "1001.md").write_text("# Findings\n\n- none\n", encoding="utf-8")

        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc_issue = mod.main(["--check", "--issue", "1001"])
            rc_branch = mod.main(["--check", "--branch", "ci/data-gap-1001-x"])
        check("cli: --issue 1001 reads findings/1001.md", rc_issue == 0, out.getvalue() + err.getvalue())
        check("cli: the branch encodes the same issue", rc_branch == 0, out.getvalue() + err.getvalue())
        check("cli: `- none` is the honest empty analysis",
              "0 finding(s)" in out.getvalue(), out.getvalue())

        (mod.FINDINGS_DIR / "1001.md").unlink()
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc_missing = mod.main(["--check", "--issue", "1001"])
        check("cli: a missing per-issue file is LOUD", rc_missing != 0, err.getvalue())
        check("cli: the failure names the per-issue path",
              "findings" in err.getvalue() and "1001.md" in err.getvalue(), err.getvalue())


def test_two_sibling_branches_touching_different_issues_do_not_collide():
    """THE GUARD: two siblings, two issues, two files — a clean merge in both orders."""
    with tempfile.TemporaryDirectory() as td:
        d = _seed_repo(Path(td), track_root=False)
        base = git(["rev-parse", "master"], d).stdout.strip()

        _sibling(d, "sibling-a", root=False, issue="1001", title="A finding")
        _sibling(d, "sibling-b", root=False, issue="1002", title="B finding")
        git(["checkout", "-q", "master"], d)

        first = _merge(d, "sibling-a")
        second = _merge(d, "sibling-b")
        check("guard: sibling A merges cleanly", first.returncode == 0, first.stdout + first.stderr)
        check("guard: sibling B merges cleanly AFTER A — no seam conflict",
              second.returncode == 0, second.stdout + second.stderr)
        check("guard: both analyses survive the merge",
              "A finding" in (d / "findings" / "1001.md").read_text(encoding="utf-8")
              and "B finding" in (d / "findings" / "1002.md").read_text(encoding="utf-8"),
              "")

        # And the same pair in the OTHER order: the seam cannot depend on who lands first.
        git(["reset", "-q", "--hard", base], d)
        first = _merge(d, "sibling-b")
        second = _merge(d, "sibling-a")
        check("guard: the reverse order also merges cleanly",
              first.returncode == 0 and second.returncode == 0,
              first.stdout + first.stderr + second.stdout + second.stderr)


def test_the_old_shared_append_point_was_the_conflict():
    """RED-first premise: the SAME two-branch shape on the old root file conflicts."""
    with tempfile.TemporaryDirectory() as td:
        d = _seed_repo(Path(td), track_root=True)
        _sibling(d, "sibling-a", root=True, issue="1001", title="A finding")
        _sibling(d, "sibling-b", root=True, issue="1002", title="B finding")
        git(["checkout", "-q", "master"], d)
        _merge(d, "sibling-a")
        second = _merge(d, "sibling-b")
        check("premise: the old root append point CONFLICTS",
              second.returncode != 0 and "findings.md" in (second.stdout + second.stderr),
              second.stdout + second.stderr)
        git(["merge", "--abort"], d)


def test_this_repository_is_on_the_per_issue_seam():
    """The seam is real here: the root file is untracked, the record and the gate agree."""
    tracked_proc = _tracked()
    check("tree: the checked-out git index is readable", tracked_proc.returncode == 0,
          tracked_proc.stderr[:300])
    tracked = tracked_proc.stdout.splitlines()
    mk = (ROOT / "Makefile").read_text(encoding="utf-8")
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    check("tree: the shared root findings.md is NOT tracked", "findings.md" not in tracked,
          " ".join(p for p in tracked if "finding" in p))
    check("tree: the historical record stays in the tree", "findings/history.md" in tracked, "")
    check("tree: a stray root findings.md is ignored, never committed",
          "\nfindings.md\n" in ignore or ignore.startswith("findings.md\n"), "")
    check("make: the plain gate forwards ISSUE so it resolves the per-issue file",
          "findings-check:" in mk and '--issue "$(ISSUE)"' in mk, "")
    check("wiring: this suite is in the `_test` chain", wired(__file__), "")


# -------------------------------------------------------------------- rulebook pin
def test_rulebook_section_8_carries_the_analysis_seam_row() -> None:
    """#1602: the §8 row naming THIS module must exist; dropping it reds `make test`."""
    print("\nRulebook: §8 carries the analysis-seam guard row (#1493/#1602)")
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    sec8 = text[text.index("## 8."):]
    row = next((ln for ln in sec8.splitlines() if "tests/test_findings_seam.py" in ln), "")
    check("§8 carries the tests/test_findings_seam.py row", bool(row),
          "AGENTS.md §8 dropped the analysis-seam guard row")
    for needle in ("test_two_sibling_branches_touching_different_issues_do_not_collide",
                   "test_the_old_shared_append_point_was_the_conflict",
                   "#1493", "#1602"):
        check(f"§8 row names {needle!r}", needle in row, row)


def main() -> int:
    print("the analysis seam is per issue (issue #1493)")
    test_each_issue_resolves_to_its_own_file()
    test_the_real_cli_checks_the_per_issue_file()
    test_two_sibling_branches_touching_different_issues_do_not_collide()
    test_the_old_shared_append_point_was_the_conflict()
    test_this_repository_is_on_the_per_issue_seam()
    test_rulebook_section_8_carries_the_analysis_seam_row()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
