#!/usr/bin/env python3
"""Where does work start? (issue #271, AGENTS.md rule 6n)

`AGENTS.md` never said where work happens. Rule 6e asked for "a feature branch cut from
`master`" — a LOCAL branch name: no `git fetch`, no assertion that the base is the current
`origin/master` tip, nothing that notices a stale or dirty tree — while `ARCHITECTURE.md`
§8 drew the life of a change as "feature branch (+ worktree off latest master)", a
mechanism no code implemented. The cost is measured: `.github/workflows/issue-bot.yml`'s
resume path ran `git checkout "$BRANCH"` in a clone that had fetched ONE ref
(`actions/checkout@v4` + `ref: master`, default `fetch-depth: 1`), so a re-run of an issue
whose branch already existed died with

    error: pathspec 'ci/data-gap-1-x' did not match any file(s) known to git

This is the ONE implementation (rules 6d/6m) of the fetch, the assertion and the refusal —
what `make base-check`, a local `make worktree-new` and the pipelines' resume all go
through:

  * `check`  — fetch the base and FAIL unless this checkout IS the fetched tip. A fresh
               `actions/checkout` is the latest `origin/master` only by accident of the
               runner; this makes it a claim that is verified, not assumed.
  * `new`    — start a NEW branch at the fetched tip: in a **worktree** (default — one
               clone cannot then serve two overlapping implementations through a shared,
               dirty tree) or in place (`--in-place`, what a fresh CI checkout does). An
               existing branch is REFUSED, never re-cut: re-cutting discards commits, and
               `resume` is what a re-run wants.
  * `resume` — an existing branch (a re-run): FETCH it first, then attach, and report how
               far behind the fetched base it is, so drift is visible instead of silent.
               Commits that exist only locally are never discarded.
  * `advance` — fetch the base and FAST-FORWARD this clean checkout onto it (issue #448).
               For a CI job that has written NOTHING yet: `refresh-bot`'s `aggregate`
               cuts its branch from the tip after ~40 min of searching, so a checkout
               that is merely BEHIND must move, not refuse — refusing there discarded a
               whole refresh (run 39329834698). It still refuses what it cannot prove
               safe: a dirty tree, or a HEAD carrying commits the base does not have.

Exit codes: 0 = the decision holds, 1 = it does not (the refusal says what to do),
2 = usage / not a git checkout.

Run: python3 scripts/worktree_base.py check      (or through `make base-check`)
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_BASE = "master"
DEFAULT_REMOTE = "origin"


class Refused(RuntimeError):
    """The decision does not hold. Exit 1; the message says what to do instead."""


try:  # the ONE definition of who a bot commits as (scripts/agent_identity.py, §7)
    from agent_identity import AGENT_EMAIL
except ImportError:  # pragma: no cover - only when run outside scripts/
    AGENT_EMAIL = "support@docondee.com"

#: The bot's name, used only when the checkout has NO configured identity. The workflow runs
#: `make git-identity` first; a bare container has nothing, and a rebase re-applies commits, so it
#: needs one (measured: `fatal: unable to auto-detect email address (got 'root@…')`).
AGENT_NAME = "Asimov Agent"


def _identity_args(cwd: str | Path | None) -> list[str]:
    """`-c user.*` only when the repo has no identity of its own — never a silent override."""
    if git(["config", "user.email"], cwd).stdout.strip():
        return []
    print("identity=fallback (no user.email configured; the rebase needs a committer)")
    return ["-c", f"user.name={AGENT_NAME}", "-c", f"user.email={AGENT_EMAIL}"]


def git(args: list[str], cwd: str | Path | None = None) -> subprocess.CompletedProcess:
    """The real `git` (the external system), never a stand-in."""
    return subprocess.run(["git", *args], cwd=str(cwd) if cwd else None,
                          capture_output=True, text=True)


def git_out(args: list[str], cwd: str | Path | None = None) -> str:
    proc = git(args, cwd)
    if proc.returncode != 0:
        raise Refused(f"`git {' '.join(args)}` failed ({proc.returncode}): "
                      f"{proc.stderr.strip() or proc.stdout.strip()}")
    return proc.stdout.strip()


def repo_root(cwd: str | Path | None = None) -> Path:
    try:
        return Path(git_out(["rev-parse", "--show-toplevel"], cwd))
    except Refused as exc:
        raise Refused(f"not a git checkout: {exc}") from exc


def fetch_base(base: str, remote: str, cwd: str | Path | None) -> str:
    """Fetch the base branch; return the commit the remote now serves for it.

    A fetch that fails is LOUD: a base that cannot be fetched cannot be asserted, and a
    stale base that passes for a fresh one is exactly the silent failure of #271.
    """
    proc = git(["fetch", remote, f"+refs/heads/{base}:refs/remotes/{remote}/{base}"], cwd)
    if proc.returncode != 0:
        raise Refused(
            f"fetching {remote}/{base} failed ({proc.returncode}): "
            f"{proc.stderr.strip() or proc.stdout.strip()}\n"
            f"  The base cannot be asserted without it — refusing to assume it is current."
        )
    return git_out(["rev-parse", f"refs/remotes/{remote}/{base}"], cwd)


def _count(a: str, b: str, cwd: str | Path | None) -> int:
    """`git rev-list --count a..b` — how many commits b has that a does not."""
    out = git_out(["rev-list", "--count", f"{a}..{b}"], cwd) or "0"
    return int(out)


def _stale(head: str, tip: str, base: str, remote: str, cwd: str | Path | None) -> Refused:
    behind = _count(head, tip, cwd)
    ahead = _count(tip, head, cwd)
    return Refused(
        f"STALE: this checkout is NOT the freshly fetched {remote}/{base}.\n"
        f"  HEAD                      {head}  ({behind} commit(s) behind, {ahead} ahead)\n"
        f"  {remote}/{base} (fetched) {tip}\n"
        f"  An implementation that starts from an old base is green locally and red on\n"
        f"  master, so this refuses instead. Start from the fetched tip:\n"
        f"    make worktree-new BRANCH=<branch>        # a worktree cut from {tip[:12]}\n"
        f"  (never re-cut an existing branch — resume it: make worktree-resume BRANCH=<branch>)"
    )


def _existing_branch(branch: str) -> Refused:
    return Refused(
        f"branch {branch} already exists — refusing to re-cut it (that discards commits).\n"
        f"  Resume it: make worktree-resume BRANCH={branch}"
    )


def git_opt(args: list[str], cwd: str | Path | None = None) -> str:
    """`git_out` for a query whose absence is an answer (a ref that may not exist)."""
    proc = git(args, cwd)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _caller(root_or_cwd: str | Path, base: str) -> dict:
    """What the checkout the caller is STANDING ON looks like, so it can be proved
    untouched: its HEAD, its branch, and the local base branch (which this seam must
    never create, move or check out — issue #271)."""
    cwd = root_or_cwd
    return {
        "head": git_out(["rev-parse", "HEAD"], cwd),
        "branch": git_opt(["symbolic-ref", "--quiet", "--short", "HEAD"], cwd),
        "local_base": git_opt(["rev-parse", "--verify", "--quiet", f"refs/heads/{base}"], cwd),
    }


def _assert_untouched(before: dict, after: dict, base: str, path: Path) -> None:
    """A worktree must not disturb the caller's checkout: not its HEAD, not the branch it
    stands on, and never the local base branch. If that ever stops being true, say so
    loudly instead of silently moving someone's work."""
    for key, what in (("head", "HEAD"), ("branch", "the branch it stands on"),
                      ("local_base", f"the local {base} branch")):
        if before[key] != after[key]:
            raise Refused(
                f"creating the worktree at {path} changed {what} of the checkout you are in:\n"
                f"  before {before[key] or '(none)'}\n"
                f"  after  {after[key] or '(none)'}\n"
                f"  That must never happen — work in a worktree BESIDE this checkout, not in it."
            )


def default_worktree_dir(root: Path, branch: str) -> Path:
    """`../<repo>-wt/<kebab>` — one parent directory holding one worktree per branch,
    BESIDE the checkout (never inside it: the pipelines stage with `git add -A`, which
    would otherwise commit the worktree into someone else's change). The shape is the one
    llgenie's rulebook uses, so an agent meets the same layout in both repos."""
    slug = re.sub(r"[^a-z0-9]+", "-", branch.lower()).strip("-") or "work"
    return root.parent / f"{root.name}-wt" / slug


def _target_dir(root: Path, branch: str, requested: str | None) -> Path:
    path = Path(requested).expanduser().resolve() if requested else default_worktree_dir(root, branch)
    if path == root.resolve() or root.resolve() in path.parents:
        raise Refused(
            f"refusing to create a worktree inside the repository ({path}).\n"
            f"  The pipelines stage with `git add -A`: a worktree under the root would be\n"
            f"  committed. Put it beside the checkout instead (drop DIR to use the default)."
        )
    return path


def _summary(branch: str, base: str, remote: str, tip: str, head: str,
             path: Path, mode: str, cwd: str | Path | None) -> None:
    print(f"mode={mode}")
    print(f"base={remote}/{base}")
    print(f"base_sha={tip}")
    print(f"branch={branch}")
    print(f"head={head}")
    print(f"path={path}")
    print(f"behind_base={_count(head, tip, cwd)}")
    print(f"OK: {branch} starts at the fetched {remote}/{base} {tip[:12]} ({path}).")


def mode_check(args: argparse.Namespace) -> int:
    cwd = os.getcwd()
    repo_root(cwd)
    tip = fetch_base(args.base, args.remote, cwd)
    head = git_out(["rev-parse", "HEAD"], cwd)
    if head != tip:
        raise _stale(head, tip, args.base, args.remote, cwd)
    print(f"base={args.remote}/{args.base}")
    print(f"base_sha={tip}")
    print(f"head={head}")
    print("fresh=true")
    print(f"OK: this checkout IS the freshly fetched {args.remote}/{args.base} ({tip[:12]}).")
    return 0


def _base_is_not_a_target(branch: str, base: str) -> None:
    """The base branch is never a worktree target: work happens on a branch OFF it, and
    checking `master` out in a second worktree would take the caller's main branch."""
    if branch == base:
        raise Refused(
            f"refusing to start `{branch}`: that is the base branch itself.\n"
            f"  A worktree carries a branch cut OFF {base}, never {base}. Pass the branch\n"
            f"  you are implementing (e.g. BRANCH=ci/issue-123-my-slug)."
        )


def mode_advance(args: argparse.Namespace) -> int:
    """Fetch the base and fast-forward a CLEAN checkout onto it (issue #448).

    `check` is right for a job with work in the tree: refusing is the safe answer to
    "start from an old base". But `refresh-bot`'s `aggregate` has written nothing when it
    asserts its base — the raw snapshots arrive afterwards as artifacts — so refusing a
    checkout that is merely BEHIND is not a safety net, it is a scheduled data loss: the
    job runs ~40 min while `master` routinely merges, and four green search legs are
    discarded (measured: run 39329834698, HEAD 2 commits behind after 4/4 legs succeeded).

    So this ADVANCES to the fetched tip, and refuses only what it cannot prove safe: a
    dirty tree (a reset would discard it) or a HEAD carrying commits the base does not
    have (it is not behind, it has diverged).
    """
    cwd = os.getcwd()
    repo_root(cwd)
    tip = fetch_base(args.base, args.remote, cwd)
    head = git_out(["rev-parse", "HEAD"], cwd)
    if head == tip:
        print(f"base={args.remote}/{args.base}")
        print(f"base_sha={tip}")
        print(f"head={head}")
        print("fresh=true")
        print(f"OK: this checkout IS the freshly fetched {args.remote}/{args.base} ({tip[:12]}).")
        return 0

    dirty = git_out(["status", "--porcelain"], cwd)
    if dirty:
        raise Refused(
            f"CANNOT ADVANCE: the tree is dirty, so fast-forwarding to "
            f"{args.remote}/{args.base} would discard it.\n"
            f"  {dirty.strip().splitlines()[0] if dirty.strip() else ''}\n"
            f"  Commit or stash it first: a job that ADVANCES has written nothing yet."
        )

    if git(["merge-base", "--is-ancestor", head, tip], cwd).returncode != 0:
        # Not behind — it has its own commits. That is the `check` refusal, verbatim.
        raise _stale(head, tip, args.base, args.remote, cwd)

    behind = _count(head, tip, cwd)
    git_out(["-c", "advice.detachedHead=false", "reset", "--hard", tip], cwd)
    after = git_out(["rev-parse", "HEAD"], cwd)
    if after != tip:
        raise Refused(f"advancing to {tip} did not take: HEAD is {after or '<unreadable>'}.")
    print(f"base={args.remote}/{args.base}")
    print(f"base_sha={tip}")
    print(f"head_before={head}")
    print(f"head={after}")
    print(f"advanced={behind}")
    print("fresh=true")
    print(f"OK: advanced {head[:12]} -> {tip[:12]} ({behind} commit(s)) onto the freshly "
          f"fetched {args.remote}/{args.base}.")
    return 0


def mode_new(args: argparse.Namespace) -> int:
    cwd = os.getcwd()
    root = repo_root(cwd)
    _base_is_not_a_target(args.branch, args.base)
    tip = fetch_base(args.base, args.remote, cwd)
    branch = args.branch

    if git(["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], cwd).returncode == 0:
        raise _existing_branch(branch)
    if git(["ls-remote", "--exit-code", "--heads", args.remote, branch], cwd).returncode == 0:
        raise _existing_branch(branch)

    if args.in_place:
        # The CI shape only: the fresh runner checkout IS the working copy, nothing else
        # is sharing it. Needs a clean HEAD (this clone never ran before) and never
        # touches the local base branch — the branch is cut from the FETCHED ref.
        head = git_out(["rev-parse", "HEAD"], cwd)
        if head != tip:
            raise _stale(head, tip, args.base, args.remote, cwd)
        git_out(["checkout", "-b", branch, f"refs/remotes/{args.remote}/{args.base}"], cwd)
        path, worktree = root, False
    else:
        path = _target_dir(root, branch, args.dir)
        if path.exists():
            raise Refused(
                f"{path} already exists — remove it, or resume the branch it holds:\n"
                f"  make worktree-resume BRANCH={branch}"
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        # The base comes from `refs/remotes/<remote>/<base>`, NEVER from the local base
        # branch: the caller's checkout is not read, moved or checked out (issue #271).
        before = _caller(cwd, args.base)
        git_out(["worktree", "add", "-b", branch, str(path),
                 f"refs/remotes/{args.remote}/{args.base}"], cwd)
        _assert_untouched(before, _caller(cwd, args.base), args.base, path)
        worktree = True

    head = git_out(["rev-parse", "HEAD"], cwd=path)
    if head != tip:  # never report a base that was not verified
        raise _stale(head, tip, args.base, args.remote, path)
    if worktree:
        print(f"worktree={path}")
        print("caller_untouched=true")
    _summary(branch, args.base, args.remote, tip, head, path, "new", cwd)
    return 0


def mode_resume(args: argparse.Namespace) -> int:
    cwd = os.getcwd()
    root = repo_root(cwd)
    _base_is_not_a_target(args.branch, args.base)
    base_tip = fetch_base(args.base, args.remote, cwd)
    branch = args.branch

    # The fetch that was missing in #271: `actions/checkout` fetches ONE ref, so a bare
    # `git checkout <branch>` has neither a local branch nor a remote-tracking ref.
    proc = git(["fetch", args.remote, f"+refs/heads/{branch}:refs/remotes/{args.remote}/{branch}"], cwd)
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip()
        raise Refused(
            f"no branch {branch} on {args.remote} — nothing to resume.\n"
            f"{detail}\n"
            f"  Start it instead: make worktree-new BRANCH={branch}"
        )
    remote_ref = f"refs/remotes/{args.remote}/{branch}"
    sha = git_out(["rev-parse", remote_ref], cwd)

    # Never discard work: a local branch carrying commits the remote does not have is
    # refused on BOTH paths (this is also why the worktree path never uses `-B`).
    local = f"refs/heads/{branch}"
    local_exists = git(["rev-parse", "--verify", "--quiet", local], cwd).returncode == 0
    if local_exists and _count(remote_ref, local, cwd) > 0:
        raise Refused(
            f"the local branch {branch} carries commits that are not on {args.remote}.\n"
            f"  Resetting it would discard them. Push them first, or resume in a worktree\n"
            f"  (drop IN_PLACE=1) where the local branch is left alone."
        )

    if args.in_place:
        # The CI shape: a fresh runner checkout with nothing else sharing it. Attach it
        # to the branch as the remote serves it — the local base branch is untouched.
        git_out(["checkout", "-B", branch, remote_ref], cwd)
        path = root
    else:
        path = _target_dir(root, branch, args.dir)
        if path.exists():
            held = git(["rev-parse", "--abbrev-ref", "HEAD"], path)
            if held.returncode != 0 or held.stdout.strip() != branch:
                raise Refused(
                    f"{path} exists and is not a worktree on {branch} "
                    f"(holds: {held.stdout.strip() or held.stderr.strip()})."
                )
        else:
            # A worktree BESIDE the caller's checkout: the work is carried by the new
            # directory, so nothing the caller stands on is switched or reset.
            path.parent.mkdir(parents=True, exist_ok=True)
            before = _caller(cwd, args.base)
            if local_exists:
                git_out(["worktree", "add", str(path), branch], cwd)
                if git_out(["rev-parse", "HEAD"], path) != sha:
                    # Fast-forward only: unique local commits were refused above, so this
                    # can never lose work.
                    git_out(["merge", "--ff-only", remote_ref], path)
            else:
                git_out(["worktree", "add", "-b", branch, str(path), remote_ref], cwd)
            _assert_untouched(before, _caller(cwd, args.base), args.base, path)

    head = git_out(["rev-parse", "HEAD"], cwd=path)
    behind = _count(head, base_tip, cwd)
    print("mode=resume")
    if path != root:
        print(f"worktree={path}")
        print("caller_untouched=true")
    print(f"base={args.remote}/{args.base}")
    print(f"base_sha={base_tip}")
    print(f"branch={branch}")
    print(f"branch_sha={sha}")
    print(f"head={head}")
    print(f"path={path}")
    print(f"at_remote_tip={str(head == sha).lower()}")
    print(f"behind_base={behind}")
    if behind:
        print(f"WARNING: {branch} is {behind} commit(s) behind {args.remote}/{args.base} "
              f"({base_tip[:12]}): merge the base before you open a PR, or CI validates a "
              f"tree that has moved.", file=sys.stderr)
    print(f"OK: resumed {branch} at {sha[:12]} ({path}).")
    return 0


def mode_adopt(args: argparse.Namespace) -> int:
    """Cut or attach the branch at COMMIT time, without re-asserting the base (issue #500).

    The implementer asserts its base at the START of a run (`mode_check`), then spends 20-30
    minutes implementing. `master` merges in the meantime — `auto-merge` runs on every green PR —
    so re-asserting `HEAD == fetched tip` at the end refused a fully implemented run and threw it
    away (run 39548077538 / issue #177: HEAD 1 commit behind, implementation lost, no PR).

    So this mode never asserts the base. It cuts the branch from the CURRENT HEAD (carrying the
    agent's uncommitted edits in place), or attaches to the branch if it already exists (a re-run),
    and REPORTS `behind_base=N` so the caller can rebase deliberately (`mode_rebase`) instead of
    being refused. The start-of-run assertion stays where it belongs (`make base-check`).
    """
    cwd = os.getcwd()
    root = repo_root(cwd)
    _base_is_not_a_target(args.branch, args.base)
    tip = fetch_base(args.base, args.remote, cwd)
    branch = args.branch
    local_ref = f"refs/heads/{branch}"
    remote_ref = f"refs/remotes/{args.remote}/{branch}"
    local_exists = git(["show-ref", "--verify", "--quiet", local_ref], cwd).returncode == 0
    remote_exists = git(["ls-remote", "--exit-code", "--heads", args.remote, branch],
                        cwd).returncode == 0

    # THE TREE IS DIRTY BY DESIGN: it holds the implementation being adopted. `git checkout`
    # (and `-B`) refuses to move HEAD when the target branch differs from the current commit
    # and the working tree would be overwritten — which is exactly the re-run shape: the
    # issue already has a branch and an open PR (issue #580, measured on run 40199055887,
    # where ~20 minutes of work were discarded with "Your local changes to the following
    # files would be overwritten by checkout"). Stash the work, attach the branch, re-apply
    # it — the work is never dropped: if the re-apply conflicts it stays in the stash AND in
    # the tree's markers, which the fix loop resolves.
    dirty = bool(git_out(["status", "--porcelain"], cwd).strip())
    carried = False
    # Only an EXISTING branch needs a checkout that moves HEAD. `checkout -b` from HEAD keeps
    # the working tree as it is, so the cut path is left exactly as it was.
    if dirty and (local_exists or remote_exists):
        stash = git(["stash", "push", "--include-untracked", "-m",
                     f"issue-bot: work carried across adopting {branch}"], cwd)
        carried = stash.returncode == 0

    if local_exists:
        git_out(["checkout", branch], cwd)
        how = "existing-local" + ("-reapplied" if carried else "")
    elif remote_exists:
        git_out(["fetch", args.remote, f"+refs/heads/{branch}:{remote_ref}"], cwd)
        git_out(["checkout", "-B", branch, remote_ref], cwd)
        how = "existing-remote" + ("-reapplied" if carried else "")
    else:
        git_out(["checkout", "-b", branch], cwd)    # from whatever HEAD holds — the agent's tree
        how = "cut-from-head"

    if carried:
        if git(["stash", "pop"], cwd).returncode != 0:
            # The stash entry SURVIVES a failed pop, so nothing is lost: the work is both in
            # `git stash list` and in the tree's conflict markers for the next round.
            conflicted = git_out(["diff", "--name-only", "--diff-filter=U"], cwd).strip()
            print(f"WARNING: re-applying this run's work onto {branch} conflicted "
                  f"({conflicted or 'see git status'}) — the work is KEPT in the stash and in the "
                  f"tree's markers; a fix round resolves it (issue #580).", file=sys.stderr)
            print("merge_conflict=true")

    head = git_out(["rev-parse", "HEAD"], cwd)
    behind = _count(head, tip, cwd)
    print("mode=adopt")
    print(f"base={args.remote}/{args.base}")
    print(f"base_sha={tip}")
    print(f"branch={branch}")
    print(f"how={how}")
    print(f"head={head}")
    print(f"behind_base={behind}")
    if behind:
        print(f"NOTE: HEAD is {behind} commit(s) behind {args.remote}/{args.base} "
              f"({tip[:12]}) — the work is KEPT; `make base-rebase BRANCH={branch}` brings it "
              f"forward before the push.", file=sys.stderr)
    print(f"OK: adopted {branch} on {head[:12]} ({how}).")
    return 0


def mode_rebase(args: argparse.Namespace) -> int:
    """Fetch the base and rebase the branch's commits onto it; a conflict KEEPS the work.

    Exit codes are the contract the caller branches on: 0 = up to date or rebased, 3 = the base
    moved and the rebase conflicted (aborted — every commit is still there, the caller pushes and
    lets the PR's fix loop repair the conflict, #475), 1 = refused (dirty tree, detached HEAD),
    2 = usage. Never a lost commit, never a silent skip.
    """
    cwd = os.getcwd()
    repo_root(cwd)
    branch = args.branch or git_out(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
    if branch in ("HEAD", "", args.base):
        raise Refused(
            f"refusing to rebase {branch or 'a detached HEAD'!r}: check the branch out first "
            f"(the base itself is never rebased by a bot)."
        )
    dirty = git(["status", "--porcelain"], cwd).stdout.strip()
    if dirty:
        raise Refused(
            "the tree has uncommitted changes, so a rebase would move work it cannot see.\n"
            "  Commit first, then rebase:\n"
            f"    git add -A && git commit -m …  &&  make base-rebase BRANCH={branch}\n"
            f"  (uncommitted: {dirty.splitlines()[0][:80]})"
        )
    tip = fetch_base(args.base, args.remote, cwd)
    head = git_out(["rev-parse", "HEAD"], cwd)
    behind = _count(head, tip, cwd)
    ahead = _count(tip, head, cwd)
    print("mode=rebase")
    print(f"base={args.remote}/{args.base}")
    print(f"base_sha={tip}")
    print(f"branch={branch}")
    print(f"head_before={head}")
    print(f"behind_base={behind}")
    print(f"ahead_base={ahead}")
    if not behind:
        print("rebase=up-to-date")
        print(f"OK: {branch} already contains {args.remote}/{args.base} ({tip[:12]}).")
        return 0
    proc = git([*_identity_args(cwd), "rebase", tip], cwd)
    if proc.returncode != 0:
        # Say WHY: a rebase that fails for a reason other than a conflict (a missing identity,
        # a hook, a permission) must be diagnosable from the step's own output.
        detail = " ".join((proc.stderr or proc.stdout or "").strip().splitlines()[-4:])
        if detail:
            print(f"rebase_detail={detail[:600]}")
        conflicted = git(["diff", "--name-only", "--diff-filter=U"], cwd).stdout.split()
        git(["rebase", "--abort"], cwd)
        # A conflict and a rebase that failed for another reason (no identity, a hook, a
        # permission) are labelled differently — both KEEP the work and push, but a reader of the
        # step's log must be able to tell which happened.
        print(f"rebase={'conflict' if conflicted else 'failed'}")
        print("conflicted=" + (",".join(conflicted) if conflicted else "none"))
        print(f"KEPT: the rebase was ABORTED — every commit on {branch} is intact at {head[:12]}, "
              f"and the push goes ahead. The PR carries the conflict, and the fix loop repairs it "
              f"(#475).", file=sys.stderr)
        return 3
    after = git_out(["rev-parse", "HEAD"], cwd)
    print("rebase=rebased")
    print(f"head_after={after}")
    print(f"OK: {branch} rebased onto {args.remote}/{args.base} ({tip[:12]}).")
    return 0


MODES = {"check": mode_check, "new": mode_new, "resume": mode_resume, "advance": mode_advance,
         "adopt": mode_adopt, "rebase": mode_rebase}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="worktree_base.py",
        description="Fetch the base and assert where work starts (AGENTS.md rule 6n).",
        epilog="Run through the Makefile: `make base-check`, `make base-advance`, "
               "`make worktree-new BRANCH=…`, `make worktree-resume BRANCH=…`, "
               "`make branch-adopt BRANCH=…`, `make base-rebase BRANCH=…`.",
    )
    parser.add_argument("mode", choices=sorted(MODES))
    parser.add_argument("--branch", help="the branch to start (new) or resume")
    parser.add_argument("--base", default=DEFAULT_BASE, help=f"base branch (default: {DEFAULT_BASE})")
    parser.add_argument("--remote", default=DEFAULT_REMOTE, help=f"remote (default: {DEFAULT_REMOTE})")
    parser.add_argument("--in-place", action="store_true",
                        help="work in this checkout instead of a worktree (the CI path)")
    parser.add_argument("--dir", help="the worktree directory (default: beside the checkout)")
    args = parser.parse_args(argv)

    if args.mode in ("new", "resume", "adopt") and not args.branch:
        print(f"Usage: worktree_base.py {args.mode} --branch <branch> "
              f"[--base {DEFAULT_BASE}] [--remote {DEFAULT_REMOTE}] [--in-place] [--dir <path>]",
              file=sys.stderr)
        return 2
    try:
        return MODES[args.mode](args)
    except Refused as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
