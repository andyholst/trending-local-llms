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
  current                — the head already carries the fetched tip: its generated artifacts are
                           regenerated if they differ from this tree's own generators (#1645)
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

A landed push is only a landed REBASE when the new head's OWN qa-validate run carries jobs
(issue #1616). The shared rebaser reads that run back from GitHub after the push (through the
ONE gh field contract, `pr_health.verify_rebased_ci`) and the verdict `rebased` — the one that
skips the squash — is reported ONLY on that proof. A push whose run has ZERO jobs is the #1115
ghost: this seam prints `verdict=ci-unverified`, leaves `rebased=false` (the head-moved gate
#1184 still skips the stale squash) and exits 1, naming the zero-jobs run.

**A CURRENT bot head gets the same regeneration (issue #1645).** Carrying `master` does not make
a generated file current: a merge wave can archive a change while the PR waits and the file still
renders an older tree, so the squash would land that drift green (`openspec-index-check` only
WARNs inside `MAX_OPENSPEC_INDEX_DRIFT`). So the `current` verdict runs the SAME sync core with
no rebase — `pr_health.regenerate_current` — which lease-pushes ONLY when one of the two
generators actually changes its file. It prints `verdict=regenerated` and the SAME
`rebased=true` squash skip (with the #1616 CI proof); an already-current pair pushes nothing and
stays `current`. A human-owned head is untouched either way: both regeneration verdicts are
returned by `classify` only for a BOT-owned head (the §6s partition).

AND THE PUSH IDENTITY IS ASSERTED FROM GITHUB'S OWN RECORD (issue #1646): the local intent
variable (`push identity: owner-pat`) is not evidence — measured on PR #1631, a push made
inside the job is recorded by GitHub as `github-actions[bot]` and still yields a 0-job
`action_required` run. So every landed push also prints the actor/triggering_actor GitHub
recorded for that run (`pr_health.read_run_identity`), the credential class it PROVES
(`checkout-credential` vs `owner-pat`), the intended class beside it, and a machine-readable
`push_identity_proved=true|false` — on BOTH the rebase and the regenerate-in-place path.

Machine-readable output (the workflow parses an allowlist of keys, rule 3d): `verdict=<name>`
and `rebased=true|false` (plus `push_identity=`/`push_identity_intended=`/`push_identity_proved=`
on any landed push). Exit codes: 0 for every report-only verdict and for a PROVED rebase;
1 for a rebase that landed without scheduling real CI; 2 only when the PR itself could not be
read.
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
        regenerate_current,
        rebase_and_push,
    )
except ImportError:  # run from the repo root
    from scripts.pr_health import (
        _gh_json,
        _git,
        branch_behind,
        is_bot_owned,
        is_conflicting,
        regenerate_current,
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


def _print_push_identity(identity: dict | None) -> None:
    """(issue #1646) ASSERT the push identity from GitHub's OWN run record, beside the class
    the local push claimed. Both are printed and both are machine-readable, so a
    `checkout-credential`-class push can never be mistaken for an `owner-pat` one."""
    if identity is None:
        return
    print(f"[auto-merge-rebase] push identity asserted from GitHub's own run "
          f"{identity['run_id']}: actor={identity['actor']} "
          f"({identity['actor_type']}), "
          f"triggering_actor={identity['triggering_actor']} -> PROVED "
          f"{identity['recorded']} (local intent: {identity['intended']})")
    print(f"push_identity={identity['recorded']}")
    print(f"push_identity_intended={identity['intended']}")
    print("push_identity_proved="
          + ("true" if identity["recorded"] == identity["intended"] else "false"))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="qa-validate auto-merge pre-squash gate: classify the PR against the "
                    "fetched master; rebase a behind-and-clean bot branch onto it and "
                    "regenerate the generated artifacts (OPENSPEC.md, ARCHITECTURE.md) on the "
                    "rebased tree before any push — and regenerate them on an already-current "
                    "bot head whose generated files differ from that tree's own generators "
                    "(issues #1049/#1601/#1645)")
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
    rc = 0

    if verdict == "behind-and-clean-bot":
        pushed, ci_verified, msg, identity = rebase_and_push(cwd, head)
        _print_push_identity(identity)
        if pushed and ci_verified is not False:
            rebased = True
            new_oid = _git(cwd, "rev-parse", f"refs/remotes/origin/{head}").stdout.strip()
            print(f"[auto-merge-rebase] rebased {head} onto the fetched master "
                  f"({new_oid[:12]}); the generated artifacts were regenerated on the rebased "
                  f"tree and the new head's own qa-validate run PROVES real CI — {msg}. This "
                  "run will NOT merge (its event head is now stale); CI on the new head will "
                  "land it.")
            verdict = "rebased"
        elif pushed and ci_verified is False:
            # (issue #1616) the branch MOVED but nothing scheduled its merge gate: the #1115
            # ghost. Never claim `rebased=true` on a push alone — the squash must not be skipped
            # on an unproven head, and the zero-jobs run has to be named where a human sees it.
            print(f"[auto-merge-rebase] FAIL: the rebase of {head} LANDED but {msg} — this run "
                  "will NOT claim it. The head-moved gate (#1184) skips the stale squash; CI on "
                  "the new head decides.")
            verdict = "ci-unverified"
            rc = 1
        else:
            print(f"[auto-merge-rebase] kept {head}: {msg} — this merge proceeds exactly as "
                  "validated; residual index drift goes to the index keeper")
            verdict = "kept"
    elif verdict == "current":
        # (issue #1645) Carrying `master` does not make a generated file current: a merge wave
        # can archive a change while the PR waits and nothing refreshed the file. The squash
        # would land that drift green, so run the SAME regeneration core with no rebase — it
        # pushes ONLY when one of the two generators actually changes its file.
        pushed, ci_verified, msg, identity = regenerate_current(cwd, head)
        _print_push_identity(identity)
        if pushed and ci_verified is not False:
            rebased = True
            new_oid = _git(cwd, "rev-parse", f"refs/remotes/origin/{head}").stdout.strip()
            print(f"[auto-merge-rebase] {head} already carries the fetched master, but its "
                  f"generated artifacts were regenerated on that tree ({new_oid[:12]}); the new "
                  f"head's own qa-validate run PROVES real CI — {msg}. This run will NOT merge "
                  "(its event head is now stale); CI on the new head will land it.")
            verdict = "regenerated"
        elif pushed and ci_verified is False:
            print(f"[auto-merge-rebase] FAIL: the regeneration of {head} LANDED but {msg} — this "
                  "run will NOT claim it. The head-moved gate (#1184) skips the stale squash; CI "
                  "on the new head decides.")
            verdict = "ci-unverified"
            rc = 1
        elif "already current on this head" in msg:
            print(f"[auto-merge-rebase] {head} already carries the fetched master and its "
                  "generated artifacts are current — merge proceeds as before")
        else:
            print(f"[auto-merge-rebase] kept {head}: {msg} — this merge proceeds exactly as "
                  "validated; residual index drift goes to the index keeper")
            verdict = "kept"
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
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
