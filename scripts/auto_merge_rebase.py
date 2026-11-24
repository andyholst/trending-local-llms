#!/usr/bin/env python3
"""#1049: auto-merge must not squash a head whose generated OPENSPEC.md predates the merge.

`qa-validate`'s `auto-merge` job squashes the PR head exactly as the author last pushed it.
A bot head's `OPENSPEC.md` was regenerated against the tree at BRANCH-CUT time, so every
change archived into `master` while the PR waited is absent from that generated file: the
squashed tree carries an index that no longer matches the tree it lands into, the master push
goes red at `openspec-index-check`, and a keeper PR cycle pays for it (measured: keepers
#1038/#1045/#1046/#1047 ping-ponged over four same-titled repairs in ~2.5 h; rebased bot
branches 45fb245/5df9735/28bf765/9a5830a went red at the index gate on 2026-11-16 because
their regenerated count lines predated later archives).

This is the merge-time seam, run by the `auto-merge` job BEFORE the squash step. It reads the
PR through `gh pr view --json` (the same payload shape `scripts/pr_health.py` classifies — one
classifier, rule 6d), fetches the PR's branch tip and `master` into the checkout, and decides
through ONE pure function (`classify`):

  not-open / draft       — nothing to do (auto-merge's own `if:` already refuses these)
  conflicting            — GitHub builds no merge commit: report-only, the branch is never rewritten
  human-owned            — a human's branch: reported, never rewritten (the §6s partition)
  refs-unreadable        — behindness is never guessed: report-only, merge proceeds as before
  current                — the head already carries the fetched tip: merge proceeds as before
  behind-and-clean-bot   — rebase onto the fetched master, REGENERATE the generated artifacts
                           (`OPENSPEC.md`, and `ARCHITECTURE.md`'s §10 block since issue #1601) ON
                           the rebased tree (the shared rebaser `pr_health.rebase_and_push` does
                           both, one implementation), commit as the agent (rule 3f) and push
                           `--force-with-lease` pinned to the fetched tip (a branch someone
                           else moved is never overwritten); then print `rebased=true`

After a landed rebase the squash step is SKIPPED by the workflow's `if:` — this run's event
head no longer matches `HEAD_SHA`, so `gh --match-head-commit` could only refuse it anyway —
the run stays green and honest, names it in the log, and the PR's CI on the new head (whose
index is merge-time-current by construction) lands the merge. A rebase git CONFLICTS on
aborts and leaves the remote branch byte-identical (issue #964's semantics): the merge then
proceeds exactly as it did before this change, and the index keeper handles residual drift.

Machine-readable output (the workflow parses an allowlist of keys, rule 3d): `verdict=<name>`
and `rebased=true|false`. Exit codes: 0 for every report-only verdict and for a landed
rebase; 2 only when the PR itself could not be read.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:  # the ONE ownership/behindness/rebase implementation (scripts/pr_health.py, rules 6d/6s)
    from pr_health import (
        _gh_json,
        _git,
        branch_behind,
        is_bot_owned,
        is_conflicting,
        rebase_and_push,
    )
except ImportError:  # run from the repo root
    from scripts.pr_health import (
        _gh_json,
        _git,
        branch_behind,
        is_bot_owned,
        is_conflicting,
        rebase_and_push,
    )

#: The PR fields this seam reads — the same shapes `pr_health.findings`/`rebase_plan` use, so
#: GitHub's mergeability vocabulary has one meaning in this repo (rule 6d).
PR_FIELDS = "number,state,isDraft,headRefName,mergeable,mergeStateStatus,headRefOid,author"


def classify(pr: dict, behind: bool | None) -> str:
    """The VERDICT seam (pure — rule 6d; the git half below only follows it).

    One of `not-open`, `draft`, `conflicting`, `human-owned`, `refs-unreadable`, `current`,
    `behind-and-clean-bot`. The order IS the policy: GitHub's own conflict ruling outranks
    ownership (a conflicting branch is fix-loop/human territory, issue #818), ownership
    outranks behindness (a human's branch is never fetched-for-action, §6s), and behindness
    that cannot be read is reported, never guessed (rule 6n).
    """
    if str(pr.get("state") or "").lower() != "open":
        return "not-open"
    if pr.get("isDraft"):
        return "draft"
    if is_conflicting(pr):
        return "conflicting"
    if not is_bot_owned(pr):
        return "human-owned"
    if behind is None:
        return "refs-unreadable"
    return "behind-and-clean-bot" if behind else "current"


def fetch_merge_refs(cwd: Path, head: str) -> bool:
    """Fetch the PR's branch tip and the base INTO this checkout (the `auto-merge` job's
    checkout is the PR's merge ref, so the job cannot assume either tip exists yet — rule 6n:
    every conclusion is drawn from the fetched TIP). Targeted refspecs: the job fetches the
    two refs the verdict needs, not the whole fleet."""
    r = _git(cwd, "fetch", "origin",
             f"+refs/heads/{head}:refs/remotes/origin/{head}",
             "+refs/heads/master:refs/remotes/origin/master")
    return r.returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="qa-validate auto-merge pre-squash gate: classify the PR against the "
                    "fetched master; rebase a behind-and-clean bot branch onto it and "
                    "regenerate the generated artifacts (OPENSPEC.md, ARCHITECTURE.md) on the "
                    "rebased tree before any push (issues #1049/#1601)")
    ap.add_argument("--pr", required=True, type=int, help="pull request number")
    ap.add_argument("--repo", default=None, help="owner/name (default: gh's own resolution)")
    ap.add_argument("--dir", default=None,
                    help="checkout to run the git half in (default: current directory)")
    args = ap.parse_args()

    repo_args = ["--repo", args.repo] if args.repo else []
    try:
        pr = _gh_json(["pr", "view", str(args.pr), *repo_args, "--json", PR_FIELDS])
    except (RuntimeError, ValueError) as exc:
        print(f"[auto-merge-rebase] FAIL: could not read PR #{args.pr}: {exc}", file=sys.stderr)
        return 2
    if not pr:
        print(f"[auto-merge-rebase] FAIL: PR #{args.pr} read returned nothing", file=sys.stderr)
        return 2

    head = str(pr.get("headRefName") or "")
    cwd = Path(args.dir) if args.dir else Path.cwd()

    behind: bool | None = None
    if (str(pr.get("state") or "").lower() == "open" and not pr.get("isDraft")
            and not is_conflicting(pr) and is_bot_owned(pr)):
        if fetch_merge_refs(cwd, head):
            behind = branch_behind(cwd, head)
        # a failed fetch leaves behind=None -> refs-unreadable: never guessed (rule 6n)

    verdict = classify(pr, behind)
    rebased = False

    if verdict == "behind-and-clean-bot":
        ok, msg = rebase_and_push(cwd, head)
        if ok:
            rebased = True
            new_oid = _git(cwd, "rev-parse", f"refs/remotes/origin/{head}").stdout.strip()
            print(f"[auto-merge-rebase] rebased {head} onto the fetched master "
                  f"({new_oid[:12]}); the generated artifacts were regenerated on the rebased "
                  f"tree — {msg}. This run will NOT merge (its event head is now stale); "
                  "CI on the new head will land it.")
            verdict = "rebased"
        else:
            print(f"[auto-merge-rebase] kept {head}: {msg} — this merge proceeds exactly as "
                  "validated; residual index drift goes to the index keeper")
            verdict = "kept"
    elif verdict == "current":
        print(f"[auto-merge-rebase] {head} already carries the fetched master — "
              "merge proceeds as before")
    elif verdict == "human-owned":
        print(f"[auto-merge-rebase] {head} is human-owned: reported, never rewritten "
              "(§6s); merge allowed only as GitHub already validated it")
    elif verdict == "conflicting":
        print(f"[auto-merge-rebase] {head} is CONFLICTING: never auto-rebased "
              "(fix loop / human territory, issue #818)")
    elif verdict == "refs-unreadable":
        print(f"[auto-merge-rebase] {head}: base/branch refs unreadable — behindness is "
              "never guessed; branch untouched, merge proceeds as validated")
    elif verdict == "draft":
        print(f"[auto-merge-rebase] PR #{pr.get('number')} is a draft — untouched")
    else:
        print(f"[auto-merge-rebase] PR #{pr.get('number')} is {pr.get('state')} — nothing to do")

    print(f"verdict={verdict}")
    print(f"rebased={'true' if rebased else 'false'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
