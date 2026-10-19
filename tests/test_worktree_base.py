#!/usr/bin/env python3
"""Where work starts: a worktree off the freshly fetched base (issue #271, rule 6n).

AGENTS.md never said where an implementation runs, and ARCHITECTURE.md §8 advertised a
"worktree off latest master" that no code implemented. The measured cost is in
`.github/workflows/issue-bot.yml`: `git checkout "$BRANCH"` in a clone that had fetched
ONE ref (`actions/checkout` + `ref: master`) dies with `pathspec ... did not match any
file(s) known to git` — and the workflow test's marker-word assertion stayed green over it.

Every case below drives the REAL `scripts/worktree_base.py` against REAL git repositories
in a temp dir (a local file remote is the external system, never a stand-in), because the
question is exactly what `git` does with a single-ref clone:

  1. `check` refuses a checkout that is behind the fetched base, and refuses loudly when
     the base cannot be fetched at all (a stale base must never pass for a fresh one);
  2. `new` creates the worktree at the FETCHED tip (the remote moves after the clone is
     taken — the clone's own tip would be the old one), and reports it;
  3. `new` refuses an existing branch (never re-cut) and a worktree inside the repository
     (the pipelines stage with `git add -A`);
  4. `resume` works where a bare `git checkout` fails — the #271 reproduction — and says
     how far behind the base the branch is;
  5. `resume` never discards commits that exist only locally;
  6. the three decisions are wired to the Makefile seam the pipelines call.

Run standalone: python3 tests/test_worktree_base.py   or   make test
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from wiring import wired  # noqa: E402  (issues #176/#192)

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "worktree_base.py"
MAKEFILE = (ROOT / "Makefile").read_text(encoding="utf-8")
ISSUE_BOT = (ROOT / ".github" / "workflows" / "issue-bot.yml").read_text(encoding="utf-8")

_PASS = 0
_FAIL = 0


def check(name: str, cond: bool, detail: object = "") -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"FAIL {name}  {detail}")


def git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """The real git. `-c user.*` so a bare runner needs no global identity."""
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t",
                           "-c", "init.defaultBranch=master", *args],
                          cwd=str(cwd), capture_output=True, text=True)


def run_script(mode: str, cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), mode, *args],
                          cwd=str(cwd), capture_output=True, text=True)


def fixture(tmp: Path) -> dict:
    """A bare remote with `master` + `ci/data-gap-1-x`, a single-ref clone (`ref: master`,
    the shape `actions/checkout@v4` leaves) and the seed checkout that moves the remote."""
    tmp.mkdir(parents=True, exist_ok=True)
    remote, seed, ci = tmp / "remote.git", tmp / "seed", tmp / "ci"
    git(["init", "-q", "--bare", str(remote)], tmp)
    git(["clone", "-q", str(remote), str(seed)], tmp)
    (seed / "f.txt").write_text("base\n")
    git(["add", "f.txt"], seed)
    git(["commit", "-qm", "base"], seed)
    git(["branch", "-m", "master"], seed)
    git(["push", "-q", "origin", "master"], seed)
    git(["checkout", "-qb", "ci/data-gap-1-x"], seed)
    (seed / "f.txt").write_text("base\nwork\n")
    git(["commit", "-qam", "work"], seed)
    git(["push", "-q", "origin", "ci/data-gap-1-x"], seed)
    git(["checkout", "-q", "master"], seed)
    # ONE ref, exactly what `actions/checkout` + `ref: master` fetches.
    git(["clone", "-q", "--single-branch", "--branch", "master", str(remote), str(ci)], tmp)
    return {"remote": remote, "seed": seed, "ci": ci}


def advance(seed: Path, text: str) -> None:
    """Move the remote's master on — the clone now holds a stale tip."""
    (seed / "f.txt").write_text((seed / "f.txt").read_text() + text)
    git(["commit", "-qam", text], seed)
    git(["push", "-q", "origin", "master"], seed)


def test_check_is_fresh_on_a_fresh_checkout(tmp: Path) -> None:
    fx = fixture(tmp)
    proc = run_script("check", fx["ci"])
    check("check: a fresh checkout IS the fetched base tip (exit 0)",
          proc.returncode == 0, proc.stderr)
    check("check: it reports the base it verified, machine-readably",
          "base_sha=" in proc.stdout and "fresh=true" in proc.stdout, proc.stdout)


def test_check_fails_on_a_checkout_behind_the_fetched_base(tmp: Path) -> None:
    fx = fixture(tmp)
    advance(fx["seed"], "moved on\n")
    proc = run_script("check", fx["ci"])
    check("check: a checkout behind the fetched base exits 1 (never assumes)",
          proc.returncode == 1, proc.stdout)
    check("check: and says 'STALE' with both commits",
          "STALE" in proc.stderr and "HEAD" in proc.stderr and "1 commit(s) behind" in proc.stderr,
          proc.stderr)
    check("check: and points at the worktree seam",
          "make worktree-new" in proc.stderr, proc.stderr)


def test_check_fails_loudly_when_the_fetch_fails(tmp: Path) -> None:
    fx = fixture(tmp)
    git(["remote", "set-url", "origin", str(tmp / "gone.git")], fx["ci"])
    proc = run_script("check", fx["ci"])
    check("check: an unfetchable base never passes", proc.returncode == 1, proc.stdout)
    check("check: the fetch failure itself is in the refusal",
          "fetching origin/master failed" in proc.stderr, proc.stderr)
    check("check: and it never reports a fresh base",
          "fresh=true" not in proc.stdout, proc.stdout)


def test_new_creates_a_worktree_at_the_fetched_tip(tmp: Path) -> None:
    fx = fixture(tmp)
    advance(fx["seed"], "moved on\n")               # the clone's own tip is now stale
    proc = run_script("new", fx["ci"], "--branch", "feat-x")
    check("new: starts a branch off the freshly FETCHED tip (exit 0)", proc.returncode == 0, proc.stderr)
    fetched = git(["rev-parse", "origin/master"], fx["ci"]).stdout.strip()
    stale = git(["rev-parse", "refs/heads/master"], fx["ci"]).stdout.strip()
    path = next((line.split("=", 1)[1] for line in proc.stdout.splitlines()
                 if line.startswith("path=")), "")
    head = git(["rev-parse", "HEAD"], Path(path)).stdout.strip() if path else ""
    check("new: the worktree HEAD is the fetched tip, not the clone's old one",
          head == fetched and fetched != stale, f"{head[:12]} {fetched[:12]} {stale[:12]}")
    check("new: it reports the base it cut from", f"base_sha={fetched}" in proc.stdout, proc.stdout)
    check("new: the worktree is registered with git",
          "feat-x" in git(["worktree", "list"], fx["ci"]).stdout, "")
    check("new: the worktree lives OUTSIDE the repository (git add -A cannot sweep it in)",
          bool(path) and not path.startswith(str(fx["ci"]) + "/"), path)
    check("new: the layout is `<repo>-wt/<kebab>`, beside the checkout (the llgenie shape)",
          Path(path).parent.name == "ci-wt" and Path(path).name == "feat-x", path)


def test_new_refuses_an_existing_branch(tmp: Path) -> None:
    fx = fixture(tmp)
    before = git(["ls-remote", "--heads", "origin", "ci/data-gap-1-x"], fx["ci"]).stdout.split()[0]
    proc = run_script("new", fx["ci"], "--branch", "ci/data-gap-1-x")
    check("new: an existing branch is refused (never re-cut)", proc.returncode == 1, proc.stdout)
    check("new: the refusal points at the resume path",
          "REFUSED" in proc.stderr and "make worktree-resume BRANCH=ci/data-gap-1-x" in proc.stderr,
          proc.stderr)
    after = git(["ls-remote", "--heads", "origin", "ci/data-gap-1-x"], fx["ci"]).stdout.split()[0]
    check("new: the existing branch is untouched", before == after, f"{before[:12]} {after[:12]}")


def test_new_never_touches_the_checkout_the_caller_stands_on(tmp: Path) -> None:
    """The worktree must not check out master, switch the caller's branch, or move the
    local base branch: it is created BESIDE the checkout the user is working in."""
    fx = fixture(tmp)
    git(["checkout", "-q", "master"], fx["ci"])
    before = {
        "head": git(["rev-parse", "HEAD"], fx["ci"]).stdout.strip(),
        "branch": git(["symbolic-ref", "--short", "HEAD"], fx["ci"]).stdout.strip(),
        "master": git(["rev-parse", "refs/heads/master"], fx["ci"]).stdout.strip(),
    }
    proc = run_script("new", fx["ci"], "--branch", "feat-safe")
    check("new: the branch starts (exit 0)", proc.returncode == 0, proc.stderr)
    after = {
        "head": git(["rev-parse", "HEAD"], fx["ci"]).stdout.strip(),
        "branch": git(["symbolic-ref", "--short", "HEAD"], fx["ci"]).stdout.strip(),
        "master": git(["rev-parse", "refs/heads/master"], fx["ci"]).stdout.strip(),
    }
    check("new: the caller's HEAD is untouched", before["head"] == after["head"], after)
    check("new: the caller is still on the branch it stood on",
          before["branch"] == after["branch"] == "master", after)
    check("new: the local base branch was neither moved nor checked out",
          before["master"] == after["master"], after)
    check("new: the base came from the remote-tracking ref, not the local branch",
          "caller_untouched=true" in proc.stdout, proc.stdout)


def test_new_and_resume_refuse_the_base_branch_itself(tmp: Path) -> None:
    fx = fixture(tmp)
    proc = run_script("new", fx["ci"], "--branch", "master")
    check("new: the base branch is refused as a target (it is never a worktree)",
          proc.returncode == 1 and "base branch itself" in proc.stderr, proc.stderr)
    proc = run_script("resume", fx["ci"], "--branch", "master")
    check("resume: the base branch is refused as a target too",
          proc.returncode == 1 and "base branch itself" in proc.stderr, proc.stderr)


def test_resume_in_a_worktree_uses_the_remote_tip(tmp: Path) -> None:
    fx = fixture(tmp)
    head = git(["rev-parse", "HEAD"], fx["ci"]).stdout.strip()
    proc = run_script("resume", fx["ci"], "--branch", "ci/data-gap-1-x")
    check("resume: a worktree resume starts (exit 0)", proc.returncode == 0, proc.stderr)
    path = next((line.split("=", 1)[1] for line in proc.stdout.splitlines()
                 if line.startswith("path=")), "")
    remote_sha = git(["rev-parse", "origin/ci/data-gap-1-x"], fx["ci"]).stdout.strip()
    check("resume: HEAD is the branch's remote commit",
          git(["rev-parse", "HEAD"], Path(path)).stdout.strip() == remote_sha, path)
    check("resume: the caller's checkout never moved",
          git(["rev-parse", "HEAD"], fx["ci"]).stdout.strip() == head and "caller_untouched=true" in proc.stdout,
          proc.stdout)


def test_resume_never_resets_a_local_branch_even_in_a_worktree(tmp: Path) -> None:
    fx = fixture(tmp)
    git(["fetch", "-q", "origin", "ci/data-gap-1-x"], fx["ci"])
    git(["checkout", "-q", "-b", "ci/data-gap-1-x", "FETCH_HEAD"], fx["ci"])
    (fx["ci"] / "local.txt").write_text("unpushed\n")
    git(["add", "local.txt"], fx["ci"])
    git(["commit", "-qm", "unpushed work"], fx["ci"])
    local_sha = git(["rev-parse", "HEAD"], fx["ci"]).stdout.strip()
    proc = run_script("resume", fx["ci"], "--branch", "ci/data-gap-1-x")
    check("resume: a local branch with unpushed work is refused in a worktree too",
          proc.returncode == 1 and "not on origin" in proc.stderr, proc.stderr)
    check("resume: the local branch is exactly where it was",
          git(["rev-parse", "ci/data-gap-1-x"], fx["ci"]).stdout.strip() == local_sha, "")
    check("resume: and no worktree was created for it",
          not (Path(fx["ci"]).parent / "ci-wt" / "ci-data-gap-1-x").exists(), "")


def test_new_refuses_a_worktree_inside_the_repo(tmp: Path) -> None:
    fx = fixture(tmp)
    proc = run_script("new", fx["ci"], "--branch", "inside", "--dir", "./wt-inside")
    check("new: a worktree inside the repository is refused", proc.returncode == 1, proc.stdout)
    check("new: and the refusal names git add -A (the reason it matters)",
          "git add -A" in proc.stderr, proc.stderr)


def test_resume_works_where_a_bare_checkout_fails(tmp: Path) -> None:
    fx = fixture(tmp)
    bare = git(["checkout", "ci/data-gap-1-x"], fx["ci"])
    check("resume: the old code FAILS on this fixture (the measured #271 path)",
          bare.returncode != 0 and "pathspec" in bare.stderr, bare.stderr)
    proc = run_script("resume", fx["ci"], "--branch", "ci/data-gap-1-x", "--in-place")
    check("resume: the same clone resumes the branch (exit 0)", proc.returncode == 0, proc.stderr)
    remote_sha = git(["rev-parse", "origin/ci/data-gap-1-x"], fx["ci"]).stdout.strip()
    check("resume: HEAD is the branch's remote commit",
          git(["rev-parse", "HEAD"], fx["ci"]).stdout.strip() == remote_sha, "")
    check("resume: it reports the branch, the base and the path",
          "branch_sha=" in proc.stdout and "base_sha=" in proc.stdout and "path=" in proc.stdout,
          proc.stdout)


def test_resume_reports_how_far_behind_the_base_it_is(tmp: Path) -> None:
    fx = fixture(tmp)
    advance(fx["seed"], "moved on\n")
    proc = run_script("resume", fx["ci"], "--branch", "ci/data-gap-1-x", "--in-place")
    check("resume: a branch behind the base still resumes", proc.returncode == 0, proc.stderr)
    check("resume: and reports behind_base= rather than staying silent",
          "behind_base=1" in proc.stdout, proc.stdout)
    check("resume: the drift is a WARNING, not a hidden fact",
          "WARNING" in proc.stderr and "behind" in proc.stderr, proc.stderr)


def test_resume_refuses_to_discard_local_commits(tmp: Path) -> None:
    fx = fixture(tmp)
    # A local branch carrying work that was never pushed (the single-ref clone needs the
    # fetch that `resume` does — so this uses git directly to build the state).
    git(["fetch", "-q", "origin", "ci/data-gap-1-x"], fx["ci"])
    made = git(["checkout", "-q", "-b", "ci/data-gap-1-x", "FETCH_HEAD"], fx["ci"])
    check("resume: fixture — a local branch with unpushed work exists", made.returncode == 0, made.stderr)
    (fx["ci"] / "local.txt").write_text("unpushed\n")
    git(["add", "local.txt"], fx["ci"])
    git(["commit", "-qm", "unpushed work"], fx["ci"])
    local_sha = git(["rev-parse", "HEAD"], fx["ci"]).stdout.strip()
    proc = run_script("resume", fx["ci"], "--branch", "ci/data-gap-1-x", "--in-place")
    check("resume: local-only commits are refused, not reset away", proc.returncode == 1, proc.stdout)
    check("resume: the refusal says why and what to do",
          "not on origin" in proc.stderr and "Push them first" in proc.stderr, proc.stderr)
    check("resume: the local commit is still there",
          (fx["ci"] / "local.txt").exists()
          and git(["rev-parse", "HEAD"], fx["ci"]).stdout.strip() == local_sha, "")


def test_resume_of_a_missing_branch_points_at_new(tmp: Path) -> None:
    fx = fixture(tmp)
    proc = run_script("resume", fx["ci"], "--branch", "nope", "--in-place")
    check("resume: a branch that does not exist is refused", proc.returncode == 1, proc.stdout)
    check("resume: and points at make worktree-new", "make worktree-new BRANCH=nope" in proc.stderr,
          proc.stderr)


def test_the_rulebook_states_the_rule() -> None:
    """The rule is only a rule if the rulebook carries it (llgenie's `test_agents_worktree`
    shape: AGENTS.md is the promise, this suite the machinery). Dropping the wording —
    "never edit the user's checkout", the worktree command, the CI assertion — must fail."""
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    rule = text[text.find("6n. **Every implementation starts in its own worktree"):]
    rule = rule[: rule.find("\n## 3. Data source")]
    check("AGENTS.md: rule 6n exists (the working copy is part of the change)", bool(rule), "")
    check("AGENTS.md: 6n forbids editing the user's checkout",
          "Never edit the user's checkout" in rule, "")
    check("AGENTS.md: 6n names the seam, not ad-hoc git",
          "make worktree-new BRANCH=" in rule and "make worktree-resume BRANCH=" in rule, "")
    check("AGENTS.md: 6n says the base is fetched and asserted",
          "freshly\n   fetched base" in rule and "make base-check" in rule, "")
    check("AGENTS.md: 6n pins one implementation (rule 6d)",
          "scripts/worktree_base.py" in rule and "tests/test_worktree_base.py" in rule, "")
    check("AGENTS.md: the section-8 guard table carries the row",
          "tests/test_worktree_base.py" in text[text.find("## 8. Regression guards"):], "")


def test_the_makefile_is_the_one_seam() -> None:
    targets = set(re.findall(r"^([A-Za-z0-9_][A-Za-z0-9_.-]*):", MAKEFILE, re.M))
    for target in ("base-check", "worktree-new", "worktree-resume"):
        check(f"Makefile: `{target}` exists (the seam CI and a human share)",
              target in targets, sorted(t for t in targets if t.startswith("worktree") or
                                        t.startswith("base")))
    for target, script in (("base-check", "check"), ("worktree-new", "new"),
                           ("worktree-resume", "resume")):
        recipe = re.search(rf"^{target}:.*\n((?:\t.*\n)+)", MAKEFILE, re.M)
        check(f"Makefile: `{target}` calls scripts/worktree_base.py {script}",
              bool(recipe) and f"worktree_base.py {script}" in recipe.group(1), "")
    check("Makefile: the test is in the `_test` chain (rule 6d — a guard nothing runs)",
          wired(__file__), "")
    check("issue-bot: the branch is cut through the Makefile seam, never a bare checkout",
          "make worktree-new" in ISSUE_BOT and 'git checkout -b "$BRANCH"' not in ISSUE_BOT, "")


def main() -> int:
    print("where work starts: a worktree off the freshly fetched base (issue #271)")
    tmp = Path(tempfile.mkdtemp(prefix="wt-base-"))
    try:
        test_check_is_fresh_on_a_fresh_checkout(tmp / "c1")
        test_check_fails_on_a_checkout_behind_the_fetched_base(tmp / "c2")
        test_check_fails_loudly_when_the_fetch_fails(tmp / "c3")
        test_new_creates_a_worktree_at_the_fetched_tip(tmp / "c4")
        test_new_refuses_an_existing_branch(tmp / "c5")
        test_new_never_touches_the_checkout_the_caller_stands_on(tmp / "c5b")
        test_new_and_resume_refuse_the_base_branch_itself(tmp / "c5c")
        test_resume_in_a_worktree_uses_the_remote_tip(tmp / "c7b")
        test_resume_never_resets_a_local_branch_even_in_a_worktree(tmp / "c9b")
        test_new_refuses_a_worktree_inside_the_repo(tmp / "c6")
        test_resume_works_where_a_bare_checkout_fails(tmp / "c7")
        test_resume_reports_how_far_behind_the_base_it_is(tmp / "c8")
        test_resume_refuses_to_discard_local_commits(tmp / "c9")
        test_resume_of_a_missing_branch_points_at_new(tmp / "c10")
        test_the_rulebook_states_the_rule()
        test_the_makefile_is_the_one_seam()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
