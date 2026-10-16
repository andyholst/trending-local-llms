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


MODES = {"check": mode_check, "new": mode_new, "resume": mode_resume}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="worktree_base.py",
        description="Fetch the base and assert where work starts (AGENTS.md rule 6n).",
        epilog="Run through the Makefile: `make base-check`, `make worktree-new BRANCH=…`, "
               "`make worktree-resume BRANCH=…`.",
    )
    parser.add_argument("mode", choices=sorted(MODES))
    parser.add_argument("--branch", help="the branch to start (new) or resume")
    parser.add_argument("--base", default=DEFAULT_BASE, help=f"base branch (default: {DEFAULT_BASE})")
    parser.add_argument("--remote", default=DEFAULT_REMOTE, help=f"remote (default: {DEFAULT_REMOTE})")
    parser.add_argument("--in-place", action="store_true",
                        help="work in this checkout instead of a worktree (the CI path)")
    parser.add_argument("--dir", help="the worktree directory (default: beside the checkout)")
    args = parser.parse_args(argv)

    if args.mode in ("new", "resume") and not args.branch:
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
