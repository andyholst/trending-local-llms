#!/usr/bin/env python3
"""ONE keeper-PR landing sequence — `make keeper-pr` (issue #869).

The keeper-PR job shape — the reviewed PR that LANDS a generated-file repair the
pipeline just computed (never merges, carries NO closing keyword, dedupes on a
branch prefix) — was hand-written three times in the workflows: `index-repair`
and `architecture-repair` in qa-validate.yml and the pipeline-failure ledger PR
in queued-alarm.yml. Three byte-similar shells meant a fix to one (the `gh pr
list` failure mode, the porcelain guard, the #960 mergeable-only dedupe) had to
be noticed and re-typed into the other two by hand (rule 6j/6d: one decision,
one implementation).

This script is that sequence. Each keeper job classifies its own drift (the
verdict stays in `openspec_index_repair.py` / `architecture_block_repair.py` /
the filer — rule 6d) and then calls:

    make keeper-pr FILE=OPENSPEC.md BRANCH_PREFIX=ci/openspec-index-repair DEDUPE=1 \
        COMMIT_MESSAGE="…" PR_TITLE="…" BODY_TARGET=openspec-index-repair-pr-body \
        BODY_ARGS="MASTER_SHA=… RUN_URL=…"

FILE names the keeper's OWNED generated files: one file, or a space-separated
set (issue #1081: the weekly architecture keeper regenerates ARCHITECTURE.md
AND OPENSPEC.md, and one invocation must land both). A single file behaves
exactly as the original single-file seam.

The sequence, in order:

  1. none of FILE's files changed (DRIFT=none landed silently) -> exit 0, no PR;
  2. a tracked change falls OUTSIDE FILE                        -> exit 1, refuse;
  3. with DEDUPE: an OPEN keeper on BRANCH_PREFIX that CAN land suppresses a
     duplicate; a DIRTY/CONFLICTING keeper is named UNMERGEABLE and a fresh
     keeper is filed (issue #960: an unmergeable keeper lands nothing);
  4. branch `<prefix>-<UTC>` from the current tip with the repo agent identity,
     ONE commit touching only FILE, pushed to origin;
  5. the PR body is produced by `make <BODY_TARGET> <BODY_ARGS…>` (the keeper's
     body decision stays in ITS script; this never composes prose) and opened
     through `gh pr create` with the caller's GH_TOKEN (the owner PAT where the
     job carries one).

Exit codes: 0 landed OR nothing-to-land OR suppressed-duplicate (each printed);
1 refused (extra changes); 2 the sequence could not run (git/gh/make failure).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from agent_identity import AGENT_EMAIL, AGENT_NAME  # the ONE identity definition


class KeeperUnavailable(Exception):
    """The sequence could not run — a defect, never a silent pass."""


def _run(cmd: list[str], root: Path, capture: bool = False) -> str:
    try:
        proc = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, check=False)
    except OSError as exc:
        raise KeeperUnavailable(f"could not run {cmd[0]}: {exc}") from exc
    if proc.returncode != 0:
        raise KeeperUnavailable(
            f"`{' '.join(cmd)}` failed (exit {proc.returncode}):\n{proc.stderr.strip()}"
        )
    return proc.stdout


def changed_tracked_files(root: Path) -> list[str]:
    """`git status --porcelain` for TRACKED changes only (untracked scratch never counts)."""
    out = _run(["git", "status", "--porcelain"], root)
    files = []
    for line in out.splitlines():
        if not line or line.startswith("??"):
            continue
        # " M path", "M  path", "MM path", "AD path"… — the path is after the XY status.
        files.append(line[3:].split(" -> ")[0].strip())
    return files


def keeper_dedupe(prefix: str, root: Path) -> tuple[int, int]:
    """(mergeable open keepers, unmergeable open keepers) on this branch prefix (#960)."""
    out = _run(
        ["gh", "pr", "list", "--state", "open",
         "--json", "headRefName,mergeStateStatus",
         "--jq", f'[.[] | select(.headRefName | startswith("{prefix}")) | .mergeStateStatus]'],
        root,
    )
    try:
        # `gh --json` prints a JSON array; parse it here instead of piping to jq so the
        # sequence depends on one external CLI (gh), not two.
        import json
        states = json.loads(out)
    except (ValueError, TypeError) as exc:
        raise KeeperUnavailable(f"keeper dedupe read unparseable: {out!r} ({exc})") from exc
    mergeable = [s for s in states if s not in ("DIRTY", "CONFLICTING")]
    unmergeable = [s for s in states if s in ("DIRTY", "CONFLICTING")]
    return len(mergeable), len(unmergeable)


def land_keeper(
    root: Path,
    files: list[str],
    branch_prefix: str,
    commit_message: str,
    pr_title: str,
    body_target: str,
    body_args: list[str],
    dedupe: bool,
) -> int:
    owned = set(files)
    changed = changed_tracked_files(root)
    landed_files = [f for f in files if f in changed]
    # 1. none of the files this keeper owns changed: the healthy case, say so and stop.
    if not landed_files:
        print(f"[keeper-pr] {' '.join(files)} carry no change against the current tree "
              "— nothing to land.")
        return 0
    # 2. refuse when a change falls outside the files this keeper owns.
    stray = [f for f in changed if f not in owned]
    if stray:
        print(f"[keeper-pr] REFUSED: changes outside {' '.join(files)} — "
              "the repair must land alone:")
        for f in changed:
            print(f"  changed: {f}")
        return 1
    # 3. one keeper per drift (#960): only a keeper that CAN land suppresses.
    if dedupe:
        mergeable, unmergeable = keeper_dedupe(branch_prefix, root)
        if mergeable:
            print(f"[keeper-pr] a mergeable keeper PR on '{branch_prefix}-…' is already open — "
                  "not opening a duplicate (one keeper per drift).")
            return 0
        if unmergeable:
            print(f"[keeper-pr] keeper-dedup #960: {unmergeable} earlier keeper(s) on "
                  f"'{branch_prefix}-…' are UNMERGEABLE (DIRTY/CONFLICTING) — they land nothing; "
                  "filing a fresh keeper against the current tip.")
    # 4. branch from the current tip, agent identity, ONE commit touching only FILE, pushed.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    branch = f"{branch_prefix}-{stamp}"
    _run(["git", "config", "user.name", AGENT_NAME], root)
    _run(["git", "config", "user.email", AGENT_EMAIL], root)
    _run(["git", "switch", "-c", branch], root)
    _run(["git", "add", "--"] + landed_files, root)
    _run(["git", "commit", "-m", commit_message], root)
    _run(["git", "push", "origin", f"HEAD:refs/heads/{branch}"], root)
    # 5. the body is the keeper's OWN target's output (no closing keyword by its contract).
    body = _run(["make", body_target] + body_args, root)
    gh = ["gh", "pr", "create", "--base", "master", "--head", branch,
          "--title", pr_title, "--body-file", "-"]
    try:
        proc = subprocess.run(gh, cwd=str(root), input=body, capture_output=True,
                              text=True, check=False)
    except OSError as exc:
        raise KeeperUnavailable(f"could not run gh: {exc}") from exc
    if proc.returncode != 0:
        raise KeeperUnavailable(
            f"gh pr create failed (branch {branch} is already pushed; the PR must be retried):\n"
            f"{proc.stderr.strip()}"
        )
    print(f"[keeper-pr] landed {' '.join(landed_files)} as keeper PR on branch "
          f"{branch}: {proc.stdout.strip()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--root", default=".", help="the repository to land in")
    ap.add_argument("--file", required=True,
                    help="the file(s) this keeper lands: one path, or a space-separated set")
    ap.add_argument("--branch-prefix", required=True, help="keeper branch prefix")
    ap.add_argument("--commit-message", required=True)
    ap.add_argument("--pr-title", required=True)
    ap.add_argument("--body-target", required=True, help="make target that prints the PR body")
    ap.add_argument("--body-arg", action="append", default=[],
                    help="extra KEY=VALUE passed to the body target (repeatable)")
    ap.add_argument("--body-args", default="",
                    help="space-separated KEY=VALUE pairs passed to the body target")
    ap.add_argument("--dedupe", action="store_true",
                    help="suppress a duplicate when a MERGEABLE keeper on the prefix is open (#960)")
    args = ap.parse_args(argv)
    try:
        return land_keeper(
            root=Path(args.root).resolve(),
            files=args.file.split(),
            branch_prefix=args.branch_prefix,
            commit_message=args.commit_message,
            pr_title=args.pr_title,
            body_target=args.body_target,
            body_args=args.body_arg + args.body_args.split(),
            dedupe=args.dedupe,
        )
    except KeeperUnavailable as exc:
        print(f"[keeper-pr] UNAVAILABLE: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
