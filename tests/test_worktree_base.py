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
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from wiring import wired  # noqa: E402  (issues #176/#192)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import worktree_base as WB  # noqa: E402  (the REAL module: #504 is about its two reads)
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


def run_script(mode: str, cwd: Path, *args: str,
               env: dict | None = None) -> subprocess.CompletedProcess:
    full = dict(os.environ)
    full.update(env or {})
    return subprocess.run([sys.executable, str(SCRIPT), mode, *args],
                          cwd=str(cwd), capture_output=True, text=True, env=full)


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


def abandoned_branch(fx: dict, name: str, n: int = 5) -> str:
    """A branch carrying `n` commits the base does not have — an abandoned attempt (#592)."""
    seed = fx["seed"]
    git(["checkout", "-q", "-b", name], seed)
    for i in range(n):
        (seed / f"stale{i}.txt").write_text(f"{i}\n")
        git(["add", "."], seed)
        git(["commit", "-qm", f"stale {i}"], seed)
    git(["push", "-q", "origin", name], seed)
    git(["checkout", "-q", "master"], seed)
    return name


def test_adopt_refuses_a_branch_that_is_not_this_runs_work(tmp: Path) -> None:
    """Issue #592: resuming an abandoned branch REMOVED every file the base had added.

    Measured on run 40210081952: `ahead_base=273`, the adopt switched the tree to the branch, and
    the step after it ran a target whose script no longer existed. The refusal must happen BEFORE
    the tree is touched, so the run's own work is still there afterwards.
    """
    fx = fixture(tmp)
    ci = fx["ci"]
    branch = abandoned_branch(fx, "ci/data-gap-9-stale", 5)
    (ci / "f.txt").write_text("base\nMINE\n")
    head_before = git(["rev-parse", "HEAD"], ci).stdout.strip()

    p = run_script("adopt", ci, "--branch", branch, env={"RESUME_MAX_AHEAD": "2"})
    check("adopt(stale): it is REFUSED, not resumed", p.returncode == 1, (p.returncode, p.stdout))
    check("adopt(stale): the message names the branch", branch in p.stderr, p.stderr[:300])
    check("adopt(stale): it says HOW FAR ahead the branch is (the evidence a human needs)",
          "5 commit(s)" in p.stderr, p.stderr[:300])
    check("adopt(stale): it names the remedy (delete the branch / --resume-stale)",
          "delete the branch" in p.stderr and "--resume-stale" in p.stderr, p.stderr[:400])
    check("adopt(stale): the run's own work is UNTOUCHED",
          (ci / "f.txt").read_text() == "base\nMINE\n", (ci / "f.txt").read_text())
    check("adopt(stale): HEAD did not move (no checkout happened)",
          git(["rev-parse", "HEAD"], ci).stdout.strip() == head_before, "")
    check("adopt(stale): no stash was created for a branch it refused to adopt",
          git(["stash", "list"], ci).stdout.strip() == "", git(["stash", "list"], ci).stdout)

    p2 = run_script("adopt", ci, "--branch", branch, "--resume-stale",
                    env={"RESUME_MAX_AHEAD": "2"})
    check("adopt(stale): --resume-stale adopts it anyway (a human's explicit call)",
          p2.returncode == 0 and "how=existing-remote" in p2.stdout, (p2.returncode, p2.stdout[-300:]))


def test_adopt_still_resumes_a_reruns_own_branch(tmp: Path) -> None:
    """The refusal must not touch the case it exists to allow: a re-run of the SAME issue."""
    fx = fixture(tmp)
    ci = fx["ci"]
    abandoned_branch(fx, "ci/data-gap-9-own", 1)     # the run's own earlier commit
    (ci / "f.txt").write_text("base\nMINE\n")
    p = run_script("adopt", ci, "--branch", "ci/data-gap-9-own", env={"RESUME_MAX_AHEAD": "2"})
    check("adopt(own): a branch carrying this run's one commit is still adopted",
          p.returncode == 0 and "how=existing-remote" in p.stdout, (p.returncode, p.stdout, p.stderr))
def test_git_out_strips_and_git_raw_does_not(tmp: Path) -> None:
    """Issue #504: `git_out` strips, so a porcelain parser built on it shifts the path.

    `git status --porcelain` writes `XY<space>PATH`: the FIRST byte of a modified entry is a
    space, and a stripped read turns `README.md` into `EADME.md`. The trap is silent, so the module
    now names both reads and this test pins the difference.
    """
    fx = fixture(tmp)
    ci = fx["ci"]
    (ci / "README.md").write_text("modified\n")     # untracked; porcelain reports "?? README.md"
    (ci / "f.txt").write_text("base\nchanged\n")   # modified: porcelain reports " M f.txt"

    raw = WB.git_raw(["status", "--porcelain"], ci)
    stripped = WB.git_out(["status", "--porcelain"], ci)
    check("git_raw: the leading status byte survives (it is DATA)",
          any(line.startswith(" M ") for line in raw.splitlines()), raw)
    check("git_out: the same read is stripped, so the leading status space is gone",
          any(line.startswith("M ") for line in stripped.splitlines()), stripped)

    # The trap itself: a naive porcelain parser on the STRIPPED read loses the first character.
    def paths_from(text: str) -> list[str]:
        return [line[3:].strip() for line in text.splitlines() if len(line) > 3]

    check("git_raw: a porcelain parser reads the whole path",
          "f.txt" in paths_from(raw) and "README.md" in paths_from(raw), paths_from(raw))
    check("git_out: the same parser mangles the first path (the #504 trap)",
          "f.txt" not in paths_from(stripped), paths_from(stripped))
    check("git_raw: `-z` records keep their NUL separators",
          "\0" in WB.git_raw(["status", "--porcelain", "-z"], ci), "")


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


def test_advance_fast_forwards_a_checkout_behind_the_base(tmp: Path) -> None:
    """The measured shape (run 39329834698): four green search legs, `master` merged
    twice while they ran. Refusing there throws the refresh away; advancing keeps it."""
    fx = fixture(tmp)
    advance(fx["seed"], "moved on\n")
    proc = run_script("advance", fx["ci"])
    check("advance: a clean checkout behind the base exits 0 (never discards the run)",
          proc.returncode == 0, proc.stderr)
    check("advance: it reports having moved, machine-readably",
          "advanced=1" in proc.stdout and "fresh=true" in proc.stdout, proc.stdout)
    head = git(["rev-parse", "HEAD"], fx["ci"]).stdout.strip()
    tip = git(["rev-parse", "origin/master"], fx["ci"]).stdout.strip()
    check("advance: HEAD IS the fetched tip afterwards", head == tip, (head, tip))
    check("advance: and the base's own content is in the tree",
          "moved on" in (fx["ci"] / "f.txt").read_text(), "")


def test_advance_is_a_no_op_on_a_fresh_checkout(tmp: Path) -> None:
    fx = fixture(tmp)
    proc = run_script("advance", fx["ci"])
    check("advance: a fresh checkout passes without moving anything",
          proc.returncode == 0 and "advanced=" not in proc.stdout, proc.stdout)


def test_advance_refuses_a_dirty_tree(tmp: Path) -> None:
    fx = fixture(tmp)
    advance(fx["seed"], "moved on\n")
    (fx["ci"] / "scratch.txt").write_text("uncommitted work\n")
    proc = run_script("advance", fx["ci"])
    check("advance: a dirty tree is REFUSED (a reset would discard it)",
          proc.returncode == 1 and "dirty" in proc.stderr, proc.stderr)
    check("advance: and the dirty file survives the refusal",
          (fx["ci"] / "scratch.txt").exists(), "")


def test_advance_refuses_a_head_with_its_own_commits(tmp: Path) -> None:
    fx = fixture(tmp)
    advance(fx["seed"], "moved on\n")
    (fx["ci"] / "g.txt").write_text("local only\n")
    git(["add", "g.txt"], fx["ci"])
    git(["commit", "-qm", "local work"], fx["ci"])
    proc = run_script("advance", fx["ci"])
    check("advance: a diverged HEAD is REFUSED (behind is not the only state)",
          proc.returncode == 1 and "STALE" in proc.stderr and "ahead" in proc.stderr, proc.stderr)
    check("advance: and the local commit is still there",
          "local work" in git(["log", "--oneline"], fx["ci"]).stdout, "")


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


def test_adopt_cuts_the_branch_from_a_behind_head_and_keeps_the_work(tmp: Path) -> None:
    """Issue #500: the run that died. master moves while the agent works; the branch is still cut
    and the work is kept — no base assertion at COMMIT time."""
    fx = fixture(tmp)
    ci = fx["ci"]
    (ci / "impl.py").write_text("print(42)\n")   # uncommitted, as the agent leaves it
    advance(fx["seed"], "moved\n")                               # a merge lands during the run
    proc = run_script("adopt", ci, "--branch", "ci/data-gap-2-x")
    check("adopt: a base that moved during the run does NOT refuse (issue #500)",
          proc.returncode == 0, proc.stderr[-300:])
    check("adopt: the branch is cut from HEAD and behind_base is REPORTED",
          "how=cut-from-head" in proc.stdout and "behind_base=1" in proc.stdout, proc.stdout)
    check("adopt: the agent's uncommitted work is still in the tree",
          (ci / "impl.py").exists(), "")
    check("adopt: HEAD is on the new branch",
          git(["rev-parse", "--abbrev-ref", "HEAD"], ci).stdout.strip() == "ci/data-gap-2-x",
          git(["rev-parse", "--abbrev-ref", "HEAD"], ci).stdout)


def test_adopt_attaches_an_existing_branch_instead_of_recutting_it(tmp: Path) -> None:
    """A re-run resumes; it never re-cuts (that would discard the earlier commits)."""
    fx = fixture(tmp)
    proc = run_script("adopt", fx["ci"], "--branch", "ci/data-gap-1-x")
    check("adopt: an existing remote branch is ATTACHED, not re-cut",
          proc.returncode == 0 and "how=existing-remote" in proc.stdout, proc.stdout)
    check("adopt: HEAD is that branch's tip, work intact",
          (fx["ci"] / "f.txt").read_text().endswith("work\n"), (fx["ci"] / "f.txt").read_text())


def test_adopt_carries_uncommitted_work_onto_an_existing_branch(tmp: Path) -> None:
    """Issue #580, measured on run 40199055887: a RE-RUN of an issue that already has a branch.

    `git checkout -B <branch> origin/<branch>` refuses when the working tree is dirty —
    and the tree is dirty BY DESIGN (it holds the implementation). The run therefore died with
    "Your local changes to the following files would be overwritten by checkout" after ~20
    minutes of work, and nothing was committed, pushed or opened as a PR.
    """
    fx = fixture(tmp)
    ci = fx["ci"]
    # `f.txt` is the file the remote branch itself changed — an uncommitted edit to it is
    # exactly what `checkout -B <branch> origin/<branch>` refuses to overwrite.
    (ci / "f.txt").write_text("base\nMINE\n")
    (ci / "impl.py").write_text("print(7)\n")          # a new file the agent added
    (ci / "notes.md").write_text("scratch\n")          # …and an untracked one

    proc = run_script("adopt", ci, "--branch", "ci/data-gap-1-x")

    # Then  it does not refuse, and the work is on the branch
    check("adopt(dirty re-run): it does NOT refuse the dirty tree (issue #580)",
          proc.returncode == 0, proc.stderr[-400:])
    check("adopt(dirty re-run): it says the work was carried across",
          "how=existing-remote-reapplied" in proc.stdout, proc.stdout)
    check("adopt(dirty re-run): HEAD is the existing branch, not a re-cut",
          git(["rev-parse", "--abbrev-ref", "HEAD"], ci).stdout.strip() == "ci/data-gap-1-x",
          git(["rev-parse", "--abbrev-ref", "HEAD"], ci).stdout)
    tip_text = git(["show", "ci/data-gap-1-x:f.txt"], ci).stdout
    check("adopt(dirty re-run): the earlier branch commit is still there",
          tip_text.endswith("work\n"), tip_text)

    # And   the agent's work is KEPT — restored cleanly, or (when it touches the same line the
    #       branch changed) preserved as a conflict the next round resolves, never dropped.
    ftext = (ci / "f.txt").read_text()
    stashed = "issue-bot: work carried" in git(["stash", "list"], ci).stdout
    check("adopt(dirty re-run): the tracked edit is kept (restored or carried, never lost)",
          "MINE" in ftext or stashed, (ftext, stashed))
    check("adopt(dirty re-run): a conflicting path keeps THIS RUN's side, not the branch's",
          ftext == "base\nMINE\n", ftext)

    # Issue #583: the commit step is `git add -A`, so a marker left in a PARSED file makes
    # every later `make` die — measured on run 40202490846 (`Makefile:588: missing separator`).
    markers = git(["grep", "-l", "^<<<<<<<"], ci).stdout.strip()
    check("adopt(dirty re-run): NO conflict marker is left in the tree (issue #583)",
          markers == "", markers)
    check("adopt(dirty re-run): the resolution is reported, naming the path(s)",
          "merge_conflict=f.txt" in proc.stdout, proc.stdout[-400:])
    check("adopt(dirty re-run): the new file survived",
          (ci / "impl.py").read_text() == "print(7)\n", (ci / "impl.py").read_text())
    check("adopt(dirty re-run): the untracked file survived",
          (ci / "notes.md").read_text() == "scratch\n", "")
    check("adopt(dirty re-run): the work is still uncommitted, for the commit step to take",
          "impl.py" in git(["status", "--porcelain"], ci).stdout,
          git(["status", "--porcelain"], ci).stdout)


def test_rebase_brings_the_commit_onto_the_fetched_tip(tmp: Path) -> None:
    fx = fixture(tmp)
    ci = fx["ci"]
    advance(fx["seed"], "moved\n")
    run_script("adopt", ci, "--branch", "b1")
    (ci / "impl.py").write_text("x\n")
    git(["add", "-A"], ci)
    git(["commit", "-qm", "impl"], ci)
    proc = run_script("rebase", ci, "--branch", "b1")
    check("rebase: a behind branch is rebased onto the fetched tip",
          proc.returncode == 0 and "rebase=rebased" in proc.stdout, proc.stdout + proc.stderr[-200:])
    check("rebase: it falls back to the repo's bot identity when the checkout has none",
          "identity=fallback" in proc.stdout, proc.stdout[:300])
    check("rebase: the base's new commit is an ancestor of HEAD",
          git(["merge-base", "--is-ancestor", "origin/master", "HEAD"], ci).returncode == 0, "")


def test_rebase_conflict_keeps_every_commit_and_says_exit_3(tmp: Path) -> None:
    """The work is NEVER lost: a conflicted rebase is aborted, and the caller pushes anyway."""
    fx = fixture(tmp)
    ci = fx["ci"]
    run_script("adopt", ci, "--branch", "b2")
    (ci / "f.txt").write_text("base\nMINE\n")
    git(["commit", "-qam", "mine"], ci)
    advance(fx["seed"], "THEIRS\n")          # same line: a real conflict
    before = git(["rev-parse", "HEAD"], ci).stdout.strip()
    proc = run_script("rebase", ci, "--branch", "b2")
    check("rebase: a conflict exits 3, so the caller still pushes",
          proc.returncode == 3, (proc.returncode, proc.stderr[-300:]))
    check("rebase: it says rebase=conflict and names the conflicted path",
          "rebase=conflict" in proc.stdout and "f.txt" in proc.stdout, proc.stdout)
    check("rebase: every commit is intact and no rebase is left in progress",
          git(["rev-parse", "HEAD"], ci).stdout.strip() == before
          and not (ci / ".git" / "rebase-merge").exists()
          and not (ci / ".git" / "rebase-apply").exists(), before)


def test_rebase_refuses_a_tree_with_uncommitted_changes(tmp: Path) -> None:
    fx = fixture(tmp)
    ci = fx["ci"]
    run_script("adopt", ci, "--branch", "b3")
    (ci / "f.txt").write_text("base\ndirty\n")
    proc = run_script("rebase", ci, "--branch", "b3")
    check("rebase: a dirty tree is REFUSED (commit first), never silently skipped",
          proc.returncode == 1 and "REFUSED" in proc.stderr, (proc.returncode, proc.stderr[-200:]))

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
    # The always-fetch half: EVERY run fetches before it starts and says which base it
    # read — the rule the worktree seam only implements for worktrees (issue #440).
    check("AGENTS.md: 6n requires a fetch before ANY work",
          "Before ANY work" in rule and "git fetch origin" in rule, "")
    check("AGENTS.md: 6n requires a fast-forward pull in a checkout you own",
          "git pull" in rule and "--ff-only" in rule, "")
    check("AGENTS.md: 6n requires the base SHA to be STATED",
          "states the base" in rule and "SHA it read" in rule, "")
    check("AGENTS.md: 6n names the machinery for a checkout you own",
          "make base-check" in rule, "")
    check("AGENTS.md: 6n says a job whose tree carries the work ADOPTS and REBASES (issue #500)",
          "make branch-adopt" in rule and "make base-rebase" in rule
          and "MUST NOT re-assert the base" in rule, "")
    check("AGENTS.md: 6e names the adopt -> commit -> rebase order (issue #500)",
          "brings the commit onto the base\n  as it is NOW" in text, "")
    check("AGENTS.md: 6e says the patch artifact is uploaded on ANY rejected push",
          "on ANY rejected push, never only the workflow-scope one" in text, "")
    check("AGENTS.md: 6n pins one implementation (rule 6d)",
          "scripts/worktree_base.py" in rule and "tests/test_worktree_base.py" in rule, "")
    check("AGENTS.md: the section-8 guard table carries the row",
          "tests/test_worktree_base.py" in text[text.find("## 8. Regression guards"):], "")


def test_the_makefile_is_the_one_seam() -> None:
    targets = set(re.findall(r"^([A-Za-z0-9_][A-Za-z0-9_.-]*):", MAKEFILE, re.M))
    for target in ("base-check", "base-advance", "worktree-new", "worktree-resume",
                   "branch-adopt", "base-rebase"):
        check(f"Makefile: `{target}` exists (the seam CI and a human share)",
              target in targets, sorted(t for t in targets if t.startswith("worktree") or
                                        t.startswith("base")))
    for target, script in (("base-check", "check"), ("base-advance", "advance"),
                           ("worktree-new", "new"), ("worktree-resume", "resume"),
                           ("branch-adopt", "adopt"), ("base-rebase", "rebase")):
        recipe = re.search(rf"^{target}:.*\n((?:\t.*\n)+)", MAKEFILE, re.M)
        check(f"Makefile: `{target}` calls scripts/worktree_base.py {script}",
              bool(recipe) and f"worktree_base.py {script}" in recipe.group(1), "")
    check("Makefile: the test is in the `_test` chain (rule 6d — a guard nothing runs)",
          wired(__file__), "")
    # Issue #500: the commit step cuts the branch AND brings it onto the base as it is NOW.
    # It must not call a BASE-ASSERTING target there — that is what discarded run 39548077538.
    commit = ISSUE_BOT[ISSUE_BOT.find("name: Commit + push the branch"):]
    commit = commit[:commit.find("name: Open the PR")]
    check("issue-bot: the commit step cuts the branch through the seam, never a bare checkout",
          "make branch-adopt" in commit and 'git checkout -b "$BRANCH"' not in commit, "")
    check("issue-bot: the commit step NEVER re-asserts the base after the work exists (issue #500)",
          "make worktree-new" not in commit and "make worktree-resume" not in commit
          and "make base-check" not in commit, commit[:400])
    check("issue-bot: the commit is rebased onto the fetched tip BEFORE the push",
          0 <= commit.find("make base-rebase") < commit.find("git push"), "")
    # The rule (#586): a conflicted rebase KEEPS every commit and the push must go ahead. The
    # step used to compare make's status to 3 — but make returns 2 for ANY failing recipe, so
    # that branch was dead code and every conflicted rebase refused the push (measured, run
    # 40205472559). The TARGET now normalises the code: `base_rebase=conflict` + exit 0.
    check("issue-bot: a conflicted rebase still pushes the work (the target owns the contract)",
          "make base-rebase" in commit and "REBASE_RC" not in commit, commit[:400])
    artifact = ISSUE_BOT[ISSUE_BOT.find("name: Upload the unpushed implementation as a patch"):]
    artifact = artifact[:artifact.find("with:")]
    check("issue-bot: the patch artifact is not gated on the workflow-scope error alone",
          "steps.push.outputs.pushed != 'true'" in artifact
          and "scope_error" not in artifact, artifact)


def main() -> int:
    print("where work starts: a worktree off the freshly fetched base (issue #271)")
    tmp = Path(tempfile.mkdtemp(prefix="wt-base-"))
    try:
        test_git_out_strips_and_git_raw_does_not(tmp / "c0c")
        test_adopt_refuses_a_branch_that_is_not_this_runs_work(tmp / "c0a")
        test_adopt_still_resumes_a_reruns_own_branch(tmp / "c0b")
        test_check_is_fresh_on_a_fresh_checkout(tmp / "c1")
        test_check_fails_on_a_checkout_behind_the_fetched_base(tmp / "c2")
        test_check_fails_loudly_when_the_fetch_fails(tmp / "c3")
        test_advance_fast_forwards_a_checkout_behind_the_base(tmp / "c3a")
        test_advance_is_a_no_op_on_a_fresh_checkout(tmp / "c3b")
        test_advance_refuses_a_dirty_tree(tmp / "c3c")
        test_advance_refuses_a_head_with_its_own_commits(tmp / "c3d")
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
        test_adopt_cuts_the_branch_from_a_behind_head_and_keeps_the_work(tmp / "c11")
        test_adopt_attaches_an_existing_branch_instead_of_recutting_it(tmp / "c12")
        test_adopt_carries_uncommitted_work_onto_an_existing_branch(tmp / "c12b")
        test_rebase_brings_the_commit_onto_the_fetched_tip(tmp / "c13")
        test_rebase_conflict_keeps_every_commit_and_says_exit_3(tmp / "c14")
        test_rebase_refuses_a_tree_with_uncommitted_changes(tmp / "c15")
        test_the_rulebook_states_the_rule()
        test_the_makefile_is_the_one_seam()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
