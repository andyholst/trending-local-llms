#!/usr/bin/env python3
"""Publish a refresh on the base as it is NOW, never on a stale one (issue #177).

A refresh PR is entirely GENERATED files — `data/models.json`, `README.md`,
`data/snapshots/*`, `data/gap_baseline.json` — that every other merge rewrites. So a
green refresh PR can become unmergeable without any defect in it: PR #164
(`ci/trending-refresh-20261014-1153`) was rebased twice inside one hour, once onto
`dce40a6` (conflicts in `README.md`, `data/models.json`, `data/gap_baseline.json`) and
again onto `3f3688c` after #168 landed, and the second run's `auto-merge` had already
failed with `GraphQL: Pull Request has merge conflicts` while `validate` and
`live-smoke` were green.

`refresh-bot`'s `aggregate` already ADVANCES its clean checkout onto the fetched base
when it starts (`make base-advance`, issue #448) — but the search legs ran before it,
and the merge, the data-gap filing and the commit all run AFTER it, so `master` can
still move under the generated tree before the PR exists. That window is this script:

  * `sync`        — fetch the base; when this checkout is behind it, RESET the tree to
                    the fetched tip and KEEP the refresh's raw snapshots (the source of
                    the data) plus `data/gap_baseline.json`, so the caller re-runs
                    `make merge` and RE-DERIVES the store, the README and the baseline
                    from them. Regenerating on the current base is what removes the
                    whole-file conflict: nothing tries to apply our version of a file
                    the merge owns. It refuses what it cannot prove safe: a HEAD with
                    commits of its own, or a dirty path outside the generated set.
  * `require-tip` — fetch the base and FAIL unless the branch already contains the
                    fetched tip. The guard that stops a queued refresh from opening a
                    PR against a `master` it has already left.

Exit codes: 0 = the decision holds, 1 = it does not (the refusal says why),
2 = usage / not a git checkout — the same contract as `worktree_base.py`.

Run through the Makefile: `make refresh-sync`, `make refresh-require-tip`.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

try:  # the ONE implementation of the fetch and of `git` (rules 6d/6m)
    from worktree_base import DEFAULT_BASE, DEFAULT_REMOTE, Refused, fetch_base, git, git_out, repo_root
except ImportError:  # pragma: no cover - only when run outside scripts/
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from worktree_base import (DEFAULT_BASE, DEFAULT_REMOTE, Refused, fetch_base, git,
                               git_out, repo_root)

#: The files a refresh GENERATES. They are re-derived from the raw snapshots by
#: `make merge`, so a reset may discard them — and NOTHING else. A path outside this
#: set is somebody's real edit, and resetting it would silently lose it.
GENERATED_PATHS = ("README.md", "data/models.json", "data/gap_baseline.json",
                   "data/snapshots/", "data/raw/", "tests/fixtures/github_meta.json")

#: The subset that is NOT re-derivable and must survive the reset: the raw snapshots
#: are the refresh's whole input, the gap baseline is analysis output whose loss
#: re-files the same gap issue the next run, and the engine-metadata fixture records
#: what `make engine-meta-capture` read from GitHub for the engines this run registers
#: (issue #334) — the reset would otherwise drop it and red the PR's `make test`.
KEEP_PATHS = ("data/raw", "data/gap_baseline.json", "tests/fixtures/github_meta.json")

RAW_NAME = re.compile(r"-(?P<stamp>\d{8}-\d{6})\.json$")


def _count(a: str, b: str) -> int:
    return int(git_out(["rev-list", "--count", f"{a}..{b}"]) or "0")


def _generated(path: str) -> bool:
    return any(path == g or path.startswith(g) for g in GENERATED_PATHS)


def _dirty_paths() -> list[str]:
    """Every path `git status` reports, as a plain relative path.

    `-z` (NUL-separated) and `--untracked-files=all` on purpose: the human format is
    `XY PATH`, so the status field's own leading space is data, and a stripped line
    loses the first character of the path (`README.md` read as `EADME.md`); without
    `--untracked-files=all` a new `scripts/` directory is reported as `scripts/` and the
    refusal cannot name the file it would have discarded.
    """
    proc = git(["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    if proc.returncode != 0:
        raise Refused(f"`git status` failed ({proc.returncode}): {proc.stderr.strip()}")
    paths: list[str] = []
    for entry in proc.stdout.split("\0"):
        if len(entry) < 4:
            continue
        path = entry[3:]  # XY<space>PATH — the space at index 2 belongs to the format
        if " -> " in path:  # a rename reports both sides
            path = path.split(" -> ", 1)[1]
        paths.append(path.strip('"'))
    return paths


def _raw_floor(raw_files: list[str]) -> str:
    """The oldest capture stamp among the refresh's raw snapshots, as an ISO8601Z.

    It is handed to `make merge SINCE=…` after a reset: the base's own `generated_utc`
    may be NEWER than our snapshots (another refresh merged while this run searched),
    and the default boundary would then skip the very data this refresh gathered.
    """
    stamps: list[datetime] = []
    for path in raw_files:
        match = RAW_NAME.search(path)
        if not match:
            continue
        try:
            stamps.append(datetime.strptime(match.group("stamp"), "%Y%m%d-%H%M%S")
                          .replace(tzinfo=timezone.utc))
        except ValueError:
            continue
    if not stamps:
        return ""
    return min(stamps).strftime("%Y-%m-%dT%H:%M:%SZ")


def _keep(cwd: str, paths: list[str], into: Path) -> list[str]:
    """Copy the paths that must survive the reset into a scratch dir; return them."""
    kept: list[str] = []
    for rel in paths:
        src = Path(cwd) / rel
        if not src.exists():
            continue
        dst = into / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
        kept.append(rel)
    return kept


def _restore(cwd: str, kept: list[str], src_root: Path) -> None:
    for rel in kept:
        src, dst = src_root / rel, Path(cwd) / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)


def mode_sync(args: argparse.Namespace) -> int:
    cwd = os.getcwd()
    repo_root(cwd)
    tip = fetch_base(args.base, args.remote, cwd)
    head = git_out(["rev-parse", "HEAD"], cwd)
    print("mode=sync")
    print(f"base={args.remote}/{args.base}")
    print(f"base_sha={tip}")
    print(f"head_before={head}")

    if head == tip:
        print(f"head={head}")
        print("sync=current")
        print(f"OK: the tree is already on the fetched {args.remote}/{args.base} ({tip[:12]}).")
        return 0

    if git(["merge-base", "--is-ancestor", head, tip], cwd).returncode != 0:
        raise Refused(
            f"CANNOT SYNC: HEAD {head[:12]} carries commits {args.remote}/{args.base} does\n"
            f"  not have, so resetting to {tip[:12]} would discard them.\n"
            f"  A refresh syncs the tree it is about to publish, before the branch exists;\n"
            f"  a branch that already has commits wants `make base-rebase BRANCH=<branch>`."
        )

    dirty = _dirty_paths()
    foreign = [p for p in dirty if not _generated(p)]
    if foreign:
        raise Refused(
            "CANNOT SYNC: the tree carries changes a refresh does not generate, and a\n"
            "  reset would discard them:\n"
            + "".join(f"    {p}\n" for p in foreign[:10])
            + "  A refresh only rewrites "
            + ", ".join(GENERATED_PATHS) + "."
        )

    raw = [p for p in dirty if p.startswith("data/raw/")]
    kept: list[str] = []
    scratch = Path(tempfile.mkdtemp(prefix="refresh-sync-"))
    try:
        kept = _keep(cwd, [p for p in KEEP_PATHS if (Path(cwd) / p).exists()], scratch)
        git_out(["-c", "advice.detachedHead=false", "reset", "--hard", tip], cwd)
        _restore(cwd, kept, scratch)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    after = git_out(["rev-parse", "HEAD"], cwd)
    if after != tip:  # never report a base that was not reached
        raise Refused(f"syncing to {tip} did not take: HEAD is {after or '<unreadable>'}.")
    floor = _raw_floor(raw)
    print(f"head={after}")
    print(f"behind_base={_count(head, after)}")
    print(f"kept={','.join(kept) if kept else 'none'}")
    print(f"raw_snapshots={len(raw)}")
    if floor:
        print(f"raw_floor={floor}")
    print("sync=reset")
    print(f"OK: the generated tree now sits on the fetched {args.remote}/{args.base} "
          f"({tip[:12]}); re-run `make merge` to re-derive the store, the README and the "
          f"baseline from the kept raw snapshots.")
    return 0


def mode_require_tip(args: argparse.Namespace) -> int:
    cwd = os.getcwd()
    repo_root(cwd)
    tip = fetch_base(args.base, args.remote, cwd)
    head = git_out(["rev-parse", "HEAD"], cwd)
    behind = _count(head, tip)
    print("mode=require-tip")
    print(f"base={args.remote}/{args.base}")
    print(f"base_sha={tip}")
    print(f"head={head}")
    print(f"behind_base={behind}")
    if behind:
        raise Refused(
            f"STALE: this branch is {behind} commit(s) behind the freshly fetched\n"
            f"  {args.remote}/{args.base} ({tip[:12]}), so the PR would rewrite generated files\n"
            f"  from an old base and GitHub would report it as conflicting after the checks\n"
            f"  went green (issue #177, PR #164).\n"
            f"  Sync the tree and re-derive it, then retry:\n"
            f"    make refresh-sync && make merge"
        )
    print("published_on_base=true")
    print(f"OK: this branch contains the fetched {args.remote}/{args.base} ({tip[:12]}).")
    return 0


MODES = {"sync": mode_sync, "require-tip": mode_require_tip}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="refresh_base.py",
        description="Publish a refresh on the fetched base, not on a stale one (issue #177).",
        epilog="Run through the Makefile: `make refresh-sync`, `make refresh-require-tip`.",
    )
    parser.add_argument("mode", choices=sorted(MODES))
    parser.add_argument("--base", default=DEFAULT_BASE, help=f"base branch (default: {DEFAULT_BASE})")
    parser.add_argument("--remote", default=DEFAULT_REMOTE, help=f"remote (default: {DEFAULT_REMOTE})")
    args = parser.parse_args(argv)
    try:
        return MODES[args.mode](args)
    except Refused as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
