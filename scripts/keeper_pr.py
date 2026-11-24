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
  3. with DEDUPE: an OPEN keeper on BRANCH_PREFIX that CAN land AND is really being
     validated suppresses a duplicate; a DIRTY/CONFLICTING keeper is named UNMERGEABLE
     and a MERGEABLE keeper whose checks never ran (or concluded red) is named a
     TOMBSTONE — both land nothing, so a fresh keeper is filed against the current tip
     (issue #960: an unmergeable keeper lands nothing; issue #1303: a checkless mergeable
     keeper pinned `master` red behind its own dedup). A MERGEABLE keeper whose head index
     count is BELOW `origin/master`'s is SUPERSEDED first (issue #1438): it is commented
     with both counts and closed, so a stale repair neither suppresses the fresh one nor
     lingers DIRTY;
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
import base64
import re
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


#: `OPENSPEC.md`'s own count line: `Active changes: **1** · archived: **486**`.
ARCHIVED_COUNT_RE = re.compile(r"archived:\s*\*\*(\d+)\*\*")


def archived_count(text: str) -> int | None:
    """The `archived: **N**` count a rendered `OPENSPEC.md` carries, or None.

    Pure (rule 6d): the dedupe and the tests read the same number.
    """
    match = ARCHIVED_COUNT_RE.search(text or "")
    return int(match.group(1)) if match else None


def repo_slug(root: Path) -> str | None:
    """`owner/repo` from origin's URL, or None when it is not a GitHub remote."""
    try:
        url = _run(["git", "remote", "get-url", "origin"], root).strip()
    except KeeperUnavailable:
        return None
    match = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$", url)
    return f"{match.group(1)}/{match.group(2)}" if match else None


def ref_archived_count(root: Path, ref: str) -> int | None:
    """The `archived:` count of `OPENSPEC.md` at a REF that is present locally."""
    proc = subprocess.run(["git", "show", f"{ref}:OPENSPEC.md"], cwd=str(root),
                          capture_output=True, text=True, check=False)
    return archived_count(proc.stdout) if proc.returncode == 0 else None


def head_archived_count(root: Path, sha: str) -> int | None:
    """The `archived:` count of `OPENSPEC.md` at a PR HEAD, read through `gh api`.

    None when the count cannot be read — an unreadable keeper is simply not classified,
    never guessed (a wrong SUPERSEDED would close a live repairer).
    """
    slug = repo_slug(root)
    if not slug or not sha:
        return None
    proc = subprocess.run(
        ["gh", "api", f"/repos/{slug}/contents/OPENSPEC.md", "-f", f"ref={sha}",
         "--jq", ".content"],
        cwd=str(root), capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0:
        return None
    try:
        text = base64.b64decode(proc.stdout.strip()).decode("utf-8", "replace")
    except (ValueError, TypeError):
        return None
    return archived_count(text)


def keeper_dedupe(prefix: str, root: Path) -> tuple[int, int, int, list[dict]]:
    """(live, tombstone, unmergeable, superseded) open keepers on this prefix.

    `live` suppresses a duplicate. A MERGEABLE keeper whose checks never ran — or concluded
    red — is a TOMBSTONE: it can never go green, so it must not hold the prefix (issue #1303:
    the checkless `ci/openspec-index-repair-20261122T041000Z` pinned `master` red behind its
    own dedup). DIRTY/CONFLICTING stays `unmergeable` (#960).

    Issue #1438 adds `superseded`: a MERGEABLE keeper whose head index count is BELOW
    `origin/master`'s. It lands nothing (the #1239 merge-tree gate reds it) yet would
    otherwise count as `live` and suppress the fresh repair — measured on `master`
    `ea82354`: `archived: **486**` vs PR #1248's `archived: **397**`. It is returned so the
    caller can comment the counts and close it; a keeper is only SUPERSEDED when BOTH
    counts are readable, never on a guess.
    """
    out = _run(
        ["gh", "pr", "list", "--state", "open",
         "--json", "number,headRefName,headRefOid,mergeStateStatus,statusCheckRollup",
         "--jq", f'[.[] | select(.headRefName | startswith("{prefix}"))]'],
        root,
    )
    try:
        # `gh --json` prints a JSON array; parse it here instead of piping to jq so the
        # sequence depends on one external CLI (gh), not two.
        import json
        rows = json.loads(out)
    except (ValueError, TypeError) as exc:
        raise KeeperUnavailable(f"keeper dedupe read unparseable: {out!r} ({exc})") from exc
    master_count = ref_archived_count(root, "origin/master")
    if master_count is None:
        print("[keeper-pr] #1438: the master index count is unreadable — no supersede "
              "classification this run", file=sys.stderr)
    live = tombstone = unmergeable = 0
    superseded: list[dict] = []
    for row in rows:
        state = str(row.get("mergeStateStatus") or "").upper()
        if state in ("DIRTY", "CONFLICTING"):
            unmergeable += 1
            continue
        head_count = head_archived_count(root, str(row.get("headRefOid") or ""))
        if master_count is not None and head_count is not None and head_count < master_count:
            superseded.append({"number": row.get("number"), "head": row.get("headRefOid"),
                               "keeper_count": head_count, "master_count": master_count})
            continue
        if keeper_health(row.get("statusCheckRollup") or []) == "live":
            live += 1
        else:
            tombstone += 1
    return live, tombstone, unmergeable, superseded


def close_superseded_keepers(root: Path, superseded: list[dict]) -> None:
    """Comment the count evidence on, then close, each SUPERSEDED keeper (#1438).

    Closing removes the PR from the OPEN set, so a re-run cannot comment twice; a failed
    close is reported, never silent.
    """
    for item in superseded:
        number, keeper, master = item["number"], item["keeper_count"], item["master_count"]
        body = (f"Closing as SUPERSEDED (issue #1438): this keeper's `OPENSPEC.md` says "
                f"`archived: **{keeper}**` while `origin/master` already says "
                f"`archived: **{master}**`. Landing it would shrink an additive value "
                f"(rule 3b), and the merge-tree index gate (#1239) reds it. No rebase, no "
                f"force-push — a fresh keeper is being filed against the current tip.")
        try:
            _run(["gh", "pr", "comment", str(number), "--body", body], root)
        except KeeperUnavailable as exc:
            print(f"[keeper-pr] #1438: could not comment on #{number}: {exc}", file=sys.stderr)
            continue
        try:
            _run(["gh", "pr", "close", str(number)], root)
            print(f"[keeper-pr] #1438: closed SUPERSEDED keeper #{number} "
                  f"(archived {keeper} < master {master}).")
        except KeeperUnavailable as exc:
            print(f"[keeper-pr] #1438: could not close #{number}: {exc}", file=sys.stderr)


#: The checks a keeper MUST carry green to be a live repairer — the two branch-protection
#: contexts (rule 1), so a keeper that cannot pass them can never land.
REQUIRED_CHECKS = ("validate", "live-smoke")
#: Conclusions that mean the head is RED, not merely unfinished.
RED_CONCLUSIONS = {"failure", "cancelled", "timed_out", "action_required", "stale",
                  "startup_failure", "neutral", "skipped"}


def keeper_health(rollup: list) -> str:
    """`'live'` when this head is really being validated; `'tombstone'` when it never was.

    Pure (rule 6d): the dedupe reads it, the tests drive it. A rollup with NO object for a
    required check is the PR #1248 shape — the run never started, so the keeper is a
    tombstone no matter what `mergeStateStatus` says. A check still queued/in progress is
    LIVE: an in-flight repairer must not be duplicated.
    """
    checks = [c for c in rollup if (c.get("name") or "") in REQUIRED_CHECKS]
    if not checks:
        return "tombstone"
    for check in checks:
        conclusion = str(check.get("conclusion") or "").lower()
        state = str(check.get("state") or "").lower()
        status = str(check.get("status") or "").lower()
        if conclusion == "success" or state == "success":
            continue
        if conclusion in RED_CONCLUSIONS or state in ("failure", "error"):
            return "tombstone"
        if conclusion or state:
            return "tombstone"
        if status in ("", "queued", "in_progress", "pending", "expected"):
            continue
        return "tombstone"
    return "live"


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
    # 3. one keeper per drift (#960, #1303): only a keeper that CAN land AND is really
    #    being validated suppresses. A DIRTY/CONFLICTING keeper is UNMERGEABLE; a MERGEABLE
    #    keeper whose checks never ran (or concluded red) is a TOMBSTONE — both land nothing,
    #    so a fresh keeper is filed against the current tip. A MERGEABLE keeper BEHIND on the
    #    archive count is SUPERSEDED first (#1438): it is commented and closed, so it neither
    #    suppresses the fresh repair nor lingers.
    if dedupe:
        live, tombstone, unmergeable, superseded = keeper_dedupe(branch_prefix, root)
        if superseded:
            print(f"[keeper-pr] keeper-dedup #1438: {len(superseded)} earlier keeper(s) on "
                  f"'{branch_prefix}-…' are SUPERSEDED (their index predates master's archive "
                  f"count) — commenting the counts and closing them.")
            close_superseded_keepers(root, superseded)
        if live:
            print(f"[keeper-pr] a live keeper PR on '{branch_prefix}-…' is already open — "
                  "not opening a duplicate (one keeper per drift).")
            return 0
        if tombstone:
            print(f"[keeper-pr] keeper-dedup #1303: {tombstone} earlier keeper(s) on "
                  f"'{branch_prefix}-…' are TOMBSTONEs (mergeable but never validated, or red) — "
                  "they can never go green; filing a fresh keeper against the current tip.")
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
