#!/usr/bin/env python3
"""Report OPEN pull requests that are SILENT — and say what to do about it (issue #442).

A PR whose merge commit GitHub cannot build (`CONFLICTING`) gets **no `pull_request` runs at
all**: `validate`, `live-smoke`, `pr-closure` and `auto-merge` are absent, not failed, so
`gh pr checks` answers `no checks reported` and the author sees an empty circle rather than a
red one. Measured on PR #439 (zero runs while conflicting) and PR #436 — where, worse, the
checks that WERE reported were green over a commit nobody had updated, because the repair went
to a differently-named local branch:

    local: fix/storage-offload-detector      (where the work started)
    PR:    fix/storage-offload-detector-413  (the name the closure checker forced)

Every local check said "up to date" while the PR kept `CONFLICTING` + `auto-merge=FAILURE`.
The queue alarm (#252) covers a stuck JOB; nothing covered a PR that runs nothing.

Exit codes: 0 = every open PR has runs and no conflict, 1 = at least one is silent (so the
scheduled run goes red), 2 = a GitHub call failed. Read-only apart from one deduplicated
comment per affected PR.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

MARKER = "pr-health-alarm"

#: How to get a silent PR moving again, in the order that works: fetch the branch, bring it up
#: to the base, push it to the PR'S HEAD — which is not necessarily the local branch's name.
FIX_HINT = ("merge origin/master into it, then `git push origin HEAD:refs/heads/<PR head>` "
            "— the PR's head branch, never a differently-named local branch")


def _gh(args: list[str]) -> str:
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def _gh_json(args: list[str]):
    return json.loads(_gh(args) or "null")


def findings(prs: list[dict], runs_for: dict[int, int]) -> list[dict]:
    """The SILENT open PRs, from the PR list and a {pr number: check-run count} map.

    Pure on purpose (rule 6d): the decision is testable without a network, and the two reasons
    are kept apart — a conflicting PR cannot run anything, while a PR with no runs and no
    conflict is a pipeline that never started (a renamed workflow, a disabled Actions tab).
    """
    out = []
    for pr in prs:
        if pr.get("isDraft"):
            continue  # a draft is allowed to be quiet; `auto-merge` refuses it anyway
        reasons = []
        mergeable = str(pr.get("mergeable") or "").upper()
        state = str(pr.get("mergeStateStatus") or "").upper()
        if mergeable == "CONFLICTING" or state == "DIRTY":
            reasons.append("CONFLICTING (GitHub builds no merge commit, so NO workflow runs)")
        if not runs_for.get(int(pr.get("number") or 0), 0):
            reasons.append("no check runs on its head commit")
        if reasons:
            out.append({"number": pr.get("number"), "head": pr.get("headRefName"),
                        "title": (pr.get("title") or "")[:70], "reasons": reasons})
    return out


def comment_body(f: dict) -> str:
    lines = [f"<!-- {MARKER} -->", "**This pull request is silent** (issue #442):", ""]
    lines += [f"- {r}" for r in f["reasons"]]
    lines += ["", f"To get it moving: `make worktree-resume BRANCH={f['head']}` to reuse the "
                  f"worktree that holds the branch, {FIX_HINT}.",
              "", "A conflicting PR runs no workflows at all, so an empty check list is not a "
                  "quiet queue — it is this."]
    return "\n".join(lines)


def has_our_marker(repo: str, number: int) -> bool:
    comments = _gh_json(["pr", "view", str(number), "--repo", repo, "--json", "comments"]) or {}
    return MARKER in json.dumps((comments or {}).get("comments") or [])


def main() -> int:
    ap = argparse.ArgumentParser(description="Report silent open pull requests (issue #442)")
    ap.add_argument("--repo", default=None, help="owner/name (default: gh's own resolution)")
    ap.add_argument("--comment", action="store_true",
                    help="leave ONE deduplicated comment per affected PR")
    args = ap.parse_args()

    repo_args = ["--repo", args.repo] if args.repo else []
    try:
        prs = _gh_json(["pr", "list", "--state", "open", "--limit", "100", *repo_args,
                        "--json", "number,title,headRefName,isDraft,mergeable,mergeStateStatus,"
                                  "headRefOid"]) or []
        runs_for = {}
        for pr in prs:
            if pr.get("isDraft"):
                continue
            oid = pr.get("headRefOid")
            runs = _gh_json(["run", "list", "--commit", str(oid), "--limit", "1",
                             *repo_args, "--json", "databaseId"]) or []
            runs_for[int(pr.get("number") or 0)] = len(runs)
    except (RuntimeError, ValueError) as exc:
        print(f"[pr-health] FAIL: {exc}", file=sys.stderr)
        return 2

    silent = findings(prs, runs_for)
    open_checked = [p for p in prs if not p.get("isDraft")]
    print(f"[pr-health] {len(open_checked)} open non-draft PR(s), {len(silent)} silent")
    for f in silent:
        print(f"  #{f['number']} {f['head']}: " + "; ".join(f["reasons"]))
    if not silent:
        return 0

    if args.comment:
        repo = args.repo or ""
        if not repo:
            try:
                repo = (_gh_json(["repo", "view", "--json", "nameWithOwner"]) or {}).get(
                    "nameWithOwner", "")
            except (RuntimeError, ValueError):
                repo = ""
        for f in silent:
            try:
                if repo and has_our_marker(repo, f["number"]):
                    print(f"  #{f['number']}: already flagged, not commenting again")
                    continue
                _gh(["pr", "comment", str(f["number"]), *repo_args, "--body", comment_body(f)])
                print(f"  #{f['number']}: flagged")
            except RuntimeError as exc:
                print(f"  #{f['number']}: could not comment ({exc})", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
