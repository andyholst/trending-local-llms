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

With `--rebase --comment` the rebaser half announces itself too (issue #964): a rebase the
sweep TRIED and could not land (git conflict, failed lease push, unreadable refs) posts ONE
marker-deduplicated comment on that PR's thread — stamped with the failed (branch, head) pair,
so a weekly round that rediscovers the same failing attempt does not re-post, while a head that
moved may be announced again. Without the announcement the only trace was a stdout line in a
scheduled run's log, and the PR stayed quietly drifted forever.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from env_int import env_int  # noqa: E402  (one reading of an integer setting — issue #487)

try:  # the ONE definition of the markers this script writes (scripts/bot_markers.py, rule 6j)
    from bot_markers import marker_name, parse_markers, start_marker
except ImportError:  # run from the repo root
    from scripts.bot_markers import marker_name, parse_markers, start_marker

MARKER = marker_name("pr-health", "alarm")
REBASE_MARKER = marker_name("pr-health", "rebase_failed")

#: How to get a silent PR moving again, in the order that works: fetch the branch, bring it up
#: to the base, push to the PR'S HEAD — which is not necessarily the local branch's name.
FIX_HINT = ("merge origin/master into it, then `git push origin HEAD:refs/heads/<PR head>` "
            "— the PR's head branch, never a differently-named local branch")

#: Bot-owned branch shapes (issue #818). Every bot/agent branch is cut through
#: `make worktree-new` or a keeper job and starts with one of these shapes:
#: `ci/data-gap-<n>-…`, `ci/keeper-…`, `ci/openspec-index-repair-…`,
#: `ci/architecture-block-repair-…` (issue-bot.yml + the keeper jobs), and the
#: agent-session conventions `tech-debt-<slug>-<issue>`, `data-gap-…`,
#: `issue-<n>-…` (measured on the merged queue: PRs #957/#955/#951/#769).
#: Any other prefix is a human-owned branch: the rebaser never
#: rewrites one (the §6r partition: "a bot PR is repaired by the sweep; a human's
#: branch is only reported").
BOT_PUSH_PREFIXES = ("ci/", "tech-debt-", "data-gap-", "issue-")


def is_bot_branch(head: str) -> bool:
    return str(head or "").startswith(BOT_PUSH_PREFIXES)


def is_conflicting(pr: dict) -> bool:
    mergeable = str(pr.get("mergeable") or "").upper()
    state = str(pr.get("mergeStateStatus") or "").upper()
    return mergeable == "CONFLICTING" or state == "DIRTY"


def rebase_plan(prs: list[dict]) -> list[dict]:
    """Which open non-draft PRs the rebaser may rewrite, and which it must not (rule 6d:
    the DECISION is pure; the git execution below only follows it).

    A CONFLICTING bot PR is NEVER auto-rebased — resolving a conflict belongs to the PR's
    own fix loop or a human (issue #818 Done-when: "a conflicted one is never rewritten").
    A non-bot branch is never rewritten either, whatever its state.
    """
    plan = []
    for pr in prs:
        if pr.get("isDraft"):
            continue
        head = str(pr.get("headRefName") or "")
        if not is_bot_branch(head):
            plan.append({"number": pr.get("number"), "head": head, "action": "human-branch"})
        elif is_conflicting(pr):
            plan.append({"number": pr.get("number"), "head": head, "action": "conflict"})
        else:
            plan.append({"number": pr.get("number"), "head": head, "action": "rebase-if-behind"})
    return plan


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


try:  # the ONE definition of who a bot commits as (scripts/agent_identity.py, §7)
    from agent_identity import AGENT_EMAIL, AGENT_NAME
except ImportError:  # run from the repo root
    from scripts.agent_identity import AGENT_EMAIL, AGENT_NAME


def _identity_flags() -> list[str]:
    """git needs an identity to REPLAY commits (rule 3f: the repo's agent commits as
    Asimov Agent). A CI container has no global git config, so the rebaser supplies the
    identity on the command line instead of assuming the checkout carries one."""
    return ["-c", f"user.name={AGENT_NAME}", "-c", f"user.email={AGENT_EMAIL}"]


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(cwd), *_identity_flags(), *args],
                          capture_output=True, text=True)


def fetch_base(cwd: Path) -> bool:
    """Fetch every branch tip and the base so behindness is decided on CURRENT refs
    (rule 6n: a conclusion is drawn from the TIP, never from whatever the clone holds)."""
    r = _git(cwd, "fetch", "origin", "+refs/heads/*:refs/remotes/origin/*")
    return r.returncode == 0


def branch_behind(cwd: Path, head: str) -> bool | None:
    """True when origin/<head> does NOT carry origin/master as an ancestor.
    None when the refs cannot be read (never guess)."""
    r = _git(cwd, "merge-base", "--is-ancestor", "refs/remotes/origin/master",
             f"refs/remotes/origin/{head}")
    if r.returncode == 0:
        return False
    if r.returncode == 1:
        return True
    return None


def rebase_and_push(cwd: Path, head: str) -> tuple[bool, str]:
    """Rebase origin/<head> onto origin/master in a scratch worktree and push it back to
    the PR's own HEAD branch (rule 6r: push to the PR's head, which re-triggers its CI).

    The scratch worktree keeps the checkout untouched; a conflict ABORTS the rebase and the
    branch is left byte-identical — the rebaser never force-pushes a conflicted result."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        wt = Path(td) / "wt"
        add = _git(cwd, "worktree", "add", "--detach", str(wt), f"refs/remotes/origin/{head}")
        if add.returncode != 0:
            return False, f"worktree add failed: {add.stderr.strip()[:120]}"
        try:
            rb = _git(wt, "rebase", "refs/remotes/origin/master")
            if rb.returncode != 0:
                _git(wt, "rebase", "--abort")
                return False, "rebase conflicted — branch left untouched (fix-loop/human work)"
            # A rebase REWRITES the branch history, so the push must be a lease push:
            # --force-with-lease pinned to the remote tip THIS run just fetched. If anyone
            # moved the branch since the fetch, the lease fails and nothing is overwritten.
            lease = _git(cwd, "rev-parse", f"refs/remotes/origin/{head}").stdout.strip()
            push = _git(wt, "push", f"--force-with-lease=refs/heads/{head}:{lease}",
                        "origin", f"HEAD:refs/heads/{head}")
            if push.returncode != 0:
                return False, f"push failed: {push.stderr.strip()[:120]}"
            return True, "rebased onto origin/master and pushed to the PR head"
        finally:
            _git(cwd, "worktree", "remove", "--force", str(wt))


def run_rebaser(cwd: Path, prs: list[dict]) -> list[dict]:
    """Execute the plan (the decision itself is `rebase_plan`, pure — rule 6d)."""
    outcomes = []
    if not fetch_base(cwd):
        print("[pr-health] FAIL: could not fetch origin refs — refusing to rebase anything "
              "(behindness is never guessed)", file=sys.stderr)
        return outcomes
    for step in rebase_plan(prs):
        if step["action"] != "rebase-if-behind":
            outcomes.append({**step, "done": step["action"]})
            continue
        behind = branch_behind(cwd, step["head"])
        if behind is None:
            outcomes.append({**step, "done": "refs unreadable — untouched"})
        elif behind is False:
            outcomes.append({**step, "done": "already current"})
        else:
            ok, msg = rebase_and_push(cwd, step["head"])
            outcomes.append({**step, "done": ("REBASED: " if ok else "kept: ") + msg})
    return outcomes


def failed_rebases(outcomes: list[dict]) -> list[dict]:
    """A rebase the sweep TRIED and could not land (issue #964): every outcome under the
    `rebase-if-behind` plan action that did not end in `REBASED:`/`already current` — git
    conflict, failed lease push, worktree failure, unreadable refs. A branch the plan refused
    to touch (a conflict GitHub already knows, a human-owned branch) was never attempted, so
    it is not a failed round."""
    return [o for o in outcomes
            if o.get("action") == "rebase-if-behind"
            and not str(o.get("done") or "").startswith("REBASED")
            and str(o.get("done") or "") != "already current"]


def rebase_run_key(head: str, oid: str) -> str:
    """The failed (branch, head) pair, as the `run=` value a marker dedup keys on (the shape
    parse_markers accepts: letters, digits, `_`, `-`). Keyed on the head oid, so one failed
    round is announced ONCE and a branch whose head later moved may be announced again."""
    safe = re.sub(r"[^A-Za-z0-9_-]+", "-", str(head or ""))
    return f"{safe}_{str(oid or '')[:12]}"


def rebase_already_announced(repo: str, number: int, run_key: str) -> bool:
    """Does this PR's thread already carry THIS round's rebase-failed marker? (read through
    the shared marker parser — reader and writer cannot drift, rule 6d/6j)."""
    comments = _gh_json(["pr", "view", str(number), "--repo", repo, "--json", "comments"]) or {}
    text = json.dumps(comments.get("comments") or [])
    return any(r["run"] == run_key for r in parse_markers(text)
               if r["bot"] == "pr-health" and r["kind"] == "rebase_failed")


def rebase_comment_body(o: dict, run_key: str) -> str:
    """Announce a failed rebaser round on the PR thread (issue #964): what git refused, that
    the branch was left untouched, and the concrete way to land it (rule 6s: conflict
    resolution belongs to the PR's own fix loop or a human)."""
    lines = [start_marker("pr-health", dt.datetime.now(dt.timezone.utc), run_key,
                          kind="rebase_failed"),
             "",
             "**The sweep tried to rebase this PR's branch and the attempt failed** "
             "(issue #964):",
             "",
             f"- `make pr-health --rebase` outcome: `{o['done']}`",
             "",
             "The branch was left **untouched** — the rebaser never force-pushes a conflicted "
             "result. To land it:",
             "",
             f"- `make worktree-resume BRANCH={o['head']}`",
             f"- `make base-rebase BRANCH={o['head']}` onto the fetched tip — a conflict aborts "
             "the rebase, keeps every commit, and is resolved by this PR's own fix loop "
             "(`scripts/fix_loop.sh`) or a human.",
             "",
             "Until it lands, every sweep round rediscovers this branch and repeats the same "
             "failing attempt with no trace outside the run log — this comment is that "
             "attempt's artifact."]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Report silent open pull requests (issue #442)")
    ap.add_argument("--repo", default=None, help="owner/name (default: gh's own resolution)")
    ap.add_argument("--comment", action="store_true",
                    help="leave ONE deduplicated comment per affected PR")
    ap.add_argument("--rebase", action="store_true",
                    help="rebase behind-and-clean BOT-owned (ci/ prefix) PR heads onto "
                         "origin/master and push them back to their PR head (issue #818); "
                         "conflicted PRs and human-owned branches are never rewritten")
    ap.add_argument("--dir", default=None,
                    help="checkout to run the git half in (default: current directory)")
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

    # THE REBASER HALF (issue #818): a behind-and-clean BOT-owned branch is rebased onto
    # the fetched base and pushed to its own PR head — GitHub starts that PR's gates
    # again. A conflicted PR and a human-owned branch are reported, never rewritten
    # (rule 6r). This is orthogonal to the silent verdict below.
    rebaser_outcomes: list[dict] = []
    if args.rebase:
        rebaser_outcomes = run_rebaser(Path(args.dir) if args.dir else Path.cwd(), prs)
        for o in rebaser_outcomes:
            print(f"  rebaser #{o['number']} {o['head']}: {o['done']}")

    repo = args.repo or ""
    if args.comment and not repo:
        try:
            repo = (_gh_json(["repo", "view", "--json", "nameWithOwner"]) or {}).get(
                "nameWithOwner", "")
        except (RuntimeError, ValueError):
            repo = ""

    # ANNOUNCE THE FAILED REBASER ROUNDS (issue #964): an attempted rebase that did not land
    # used to exist only as one stdout line in a scheduled run's log, so the next round
    # rediscovers the same branch and repeats the same failing attempt forever. With
    # --comment each failed (branch, head) gets ONE marker-deduplicated comment on its own
    # PR thread, naming the remedy. This is the comment half of the rebaser; the verdict
    # below stays untouched.
    if args.comment:
        oids = {int(p.get("number") or 0): str(p.get("headRefOid") or "") for p in prs}
        for o in failed_rebases(rebaser_outcomes):
            key = rebase_run_key(o["head"], oids.get(int(o["number"] or 0), ""))
            try:
                if repo and rebase_already_announced(repo, int(o["number"]), key):
                    print(f"  #{o['number']}: failed rebase already announced for {key} — "
                          "not commenting again")
                    continue
                _gh(["pr", "comment", str(o["number"]), *repo_args, "--body",
                     rebase_comment_body(o, key)])
                print(f"  #{o['number']}: announced the failed rebase on the PR thread")
            except RuntimeError as exc:
                print(f"  #{o['number']}: could not announce the failed rebase ({exc})",
                      file=sys.stderr)

    if not silent:
        return 0

    # Silent-PR flagging (issue #814 retired the dispatched repairer): the sweep comments
    # the remedy; conflict resolution belongs to the PR's own implementer loop
    # (`issue-bot.yml` + `scripts/fix_loop.sh`) or to a human. Behind-and-clean bot branches
    # are repaired here by the rebaser above (issue #818).
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
