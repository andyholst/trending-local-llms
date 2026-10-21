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
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from env_int import env_int  # noqa: E402  (one reading of an integer setting — issue #487)

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


#: Branches this repo's bots push. A PR from one of them can be REPAIRED by the bot
#: (issue #475); a human's branch is only reported, because the loop would push to it.
BOT_BRANCH = re.compile(r"^ci/")


def repair_targets(silent: list[dict]) -> list[dict]:
    """The silent PRs a bot may repair itself — its own `ci/…` branches, nothing else.

    A conflicting PR runs NO workflows (issue #442), so `qa-validate` can never dispatch
    `fix-bot` for it: the only trigger that fires is this sweep. Naming the rule here keeps
    it testable without a network (rule 6d), and a human's branch is left alone.
    """
    return [f for f in silent if BOT_BRANCH.match(str(f.get("head") or ""))]


def fixbot_commits(repo: str, number: int) -> int:
    """How many `fix-bot:` commits the PR already carries (the dispatcher's cap, issue #383)."""
    commits = _gh_json(["api", f"repos/{repo}/pulls/{number}/commits?per_page=100",
                        "--jq", '[.[] | select(.commit.message | startswith("fix-bot:"))] | length'])
    return int(commits or 0)


def dispatch_repair(repo: str, f: dict, cap: int) -> str:
    """Dispatch `fix-bot` for ONE silent PR. Returns what happened, for the log."""
    number = int(f["number"])
    try:
        done = fixbot_commits(repo, number)
    except (RuntimeError, ValueError) as exc:
        return f"could not count fix-bot commits ({exc})"
    if done >= cap:
        return f"{done} fix-bot commit(s) already, cap {cap} — left for a human"
    try:
        _gh(["workflow", "run", "fix-bot.yml", "--repo", repo,
             "-f", f"pr_number={number}", "-f", f"branch={f['head']}"])
    except RuntimeError as exc:
        return f"dispatch failed ({exc})"
    return "dispatched fix-bot"


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
    ap.add_argument("--repair", action="store_true",
                    help="dispatch fix-bot for a silent PR on a bot branch (issue #475); "
                         "capped at MAX_FIXBOT_COMMITS fix-bot commits per PR")
    ap.add_argument("--max-fixbot-commits", type=int,
                    default=env_int("MAX_FIXBOT_COMMITS", 2),
                    help="fix-bot commits allowed per PR before the sweep stops (default 2)")
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

    repo = args.repo or ""
    if not repo and (args.comment or args.repair):
        try:
            repo = (_gh_json(["repo", "view", "--json", "nameWithOwner"]) or {}).get(
                "nameWithOwner", "")
        except (RuntimeError, ValueError):
            repo = ""

    # REPAIR FIRST (issue #475): a bot-owned PR that cannot merge because its base moved is
    # a job for the bot, not for a human — and this sweep is the only trigger that fires at
    # all for a conflicting PR. The comment below stays as the record (and as the fallback
    # when the cap is reached or the branch is not ours).
    if args.repair and repo:
        targets = repair_targets(silent)
        others = len(silent) - len(targets)
        print(f"[pr-health] repair: {len(targets)} bot PR(s) dispatchable"
              + (f", {others} left for a human (not a ci/ branch)" if others else ""))
        for f in targets:
            print(f"  #{f['number']} {f['head']}: {dispatch_repair(repo, f, args.max_fixbot_commits)}")

    if args.comment:
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
