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

The THIRD silence (issue #1123): a PR whose head commit edits `.github/workflows/` and whose
commit author GitHub maps to an outside contributor gets every pipeline run on that head HELD
in `action_required` — GitHub asks a collaborator to approve the branch's own workflows before
any job executes. The runs EXIST but executed nothing: `gh pr checks` is empty,
`mergeStateStatus` is `UNSTABLE` forever, and the old sweep read the run COUNT and called it
healthy. Measured on PR #1116 (head `b10716488d`, 2026-11-17): `qa-validate` run 44037397846
and `pr-closure` run completed `action_required`, zero jobs, no alarm anywhere. The sweep now
flags a head whose every run is `action_required` and names the human remedy (approve the
pending runs) — approving is a collaborator's act (rule 6t), so the sweep announces, never acts.

The FOURTH state a draft fleet PR is not a silence but a STALL (owner directive 2026-11-24,
issue #1563): a draft is invisible to reviewers and `auto-merge`'s own `if:` (`draft == false`)
refuses it, so a finished change can sit on the board green-and-unlandable. `findings` has
always SKIPPED drafts ("a draft is allowed to be quiet"), which is exactly why nothing named
one. `draft_findings()` is the other half of the classification: a draft that CARRIES a bound
issue (`closingIssuesReferences`, or the issue its branch encodes) is named with that issue —
fleet PRs go up READY, never draft; a genuinely unfinished draft binds no issue and stays out
of the verdict.

THE REBASER PROVES ITS OWN CI (issue #1616): `--rebase` pushes a behind-and-clean bot head back
to its PR, and since #1115 that push carries the owner PAT — a job-token push is what created
the 0-job `action_required` ghosts. A PAT push is necessary and NOT sufficient: `rebase_and_push`
now READS the pushed sha's own `qa-validate` run back from GitHub (`verify_rebased_ci`, through
the ONE gh field contract) and reports the rebase as verified only when that run carries >0
jobs. A ghost, an unreadable jobs answer or a run that never appears inside the bounded wait is
reported as UNVERIFIED, never as a clean `REBASED:` — the caller (`auto_merge_rebase`) then
refuses to claim `rebased=true` and the loud line names the zero-jobs run.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gh_json_fields  # noqa: E402  (the ONE gh --json field contract — issue #1158)
from env_int import env_int  # noqa: E402  (one reading of an integer setting — issue #487)

try:  # the ONE definition of the markers this script writes (scripts/bot_markers.py, rule 6j)
    from bot_markers import marker_name, parse_markers, start_marker
    from agent_identity import AGENT_LOGINS  # the ONE definition of the agent login (#1349)
except ImportError:  # run from the repo root
    from scripts.bot_markers import marker_name, parse_markers, start_marker
    from scripts.agent_identity import AGENT_LOGINS

MARKER = marker_name("pr-health", "alarm")
REBASE_MARKER = marker_name("pr-health", "rebase_failed")
#: The third silence (issue #1123): every run on the head is `action_required` — GitHub is
#: holding the branch's own workflows for approval, so the runs exist and executed nothing.
APPROVAL_HOLD_REASON = ("pipelines HELD FOR APPROVAL (every run on its head commit is "
                        "`action_required` — GitHub executed no jobs)")

#: The workflow whose JOBS a rebased PR head must schedule (issue #1616). A push that moves a
#: branch and creates a run with ZERO jobs is the #1115 ghost: `gh pr checks` answers "no
#: checks reported" and `auto-merge` can never land the head.
QA_VALIDATE_WORKFLOW = "qa-validate.yml"
#: Bounded wait for the pushed head's OWN run to appear before CI scheduling is called UNPROVEN.
#: Short enough to keep a sweep round fast, long enough for a real scheduler to create the run.
CI_VERIFY_WAIT_SECONDS = 60
CI_VERIFY_INTERVAL_SECONDS = 3
#: Built through the ONE gh field contract (rule 6d): `make lint`'s scan reads every
#: `gh … --json` request in `scripts/`, so a field list this module spells by hand would be a
#: finding. Assembled HERE, once, for the two requests the CI proof makes.
_CI_RUN_FIELDS = gh_json_fields.request(
    "run list", "databaseId,headBranch,headSha,workflowName,status,conclusion,createdAt,url")
_CI_JOBS_FIELDS = gh_json_fields.request("run view", "jobs")

#: How to get a silent PR moving again, in the order that works: fetch the branch, bring it up
#: to the base, push to the PR'S HEAD — which is not necessarily the local branch's name.
FIX_HINT = ("merge origin/master into it, then `git push origin HEAD:refs/heads/<PR head>` "
            "— the PR's head branch, never a differently-named local branch")

#: Bot-owned PRs are decided by the AUTHOR, not by a branch-name convention (issue #1295).
#: `author.is_bot` is sufficient, but it is NOT necessary: the agent login is a GitHub *User*
#: (measured `.user.type` -> `User`), so every agent PR answers `is_bot: false` and a key on
#: `is_bot` alone classified all 22 open PRs as human-owned (issue #1349). The author LOGIN,
#: checked against `scripts/agent_identity.py`'s ONE agent set, is the field that actually
#: separates the agent from the owner. The prefix list stays a fallback for callers that pass
#: a head without author data (and for the pure tests).
BOT_PUSH_PREFIXES = ("ci/", "tech-debt-", "data-gap-", "issue-")


def is_bot_branch(head: str) -> bool:
    return str(head or "").startswith(BOT_PUSH_PREFIXES)


def is_bot_owned(pr: dict) -> bool:
    """Who owns this PR: its GitHub author when known, the prefix otherwise (#1295/#1349).

    A PR object from `gh pr list --json …,author` carries `author.is_bot`; that is
    sufficient. It is not necessary: the agent login `asimov-agent` is a GitHub **User**, so
    `is_bot` is `false` for every agent PR and the login must be checked too (issue #1349).
    When no author data is present at all, fall back to `is_bot_branch` so older callers and
    fixtures keep their meaning — never infer a human is a bot from a name.
    """
    author = pr.get("author") if isinstance(pr, dict) else None
    if isinstance(author, dict):
        if author.get("is_bot") is True:
            return True
        login = str(author.get("login") or "").strip().lower()
        if login:
            return login in AGENT_LOGINS
    return is_bot_branch(str(pr.get("headRefName") or ""))


def is_conflicting(pr: dict) -> bool:
    mergeable = str(pr.get("mergeable") or "").upper()
    state = str(pr.get("mergeStateStatus") or "").upper()
    return mergeable == "CONFLICTING" or state == "DIRTY"


#: The issue a PR is BOUND to (owner directive 2026-11-24, issue #1563): GitHub's own
#: `closingIssuesReferences`, else the issue its branch encodes (`scripts/pr_closure.py`'s ONE
#: parser). A keeper/refresh/docs branch encodes none and binds nothing, so it is never named.
try:  # the ONE branch→issue parser (rule 6d), read from pr_closure when importable
    from pr_closure import implemented_issue as _implemented_issue
except ImportError:  # run from the repo root
    from scripts.pr_closure import implemented_issue as _implemented_issue


def bound_issues(pr: dict) -> list[int]:
    """The issues this PR binds, in order — GitHub's own binding FIRST (#1563).

    `closingIssuesReferences` is GitHub's record of the closing keyword, so it outranks a
    branch-name convention; the branch parser covers the local/fixture shape and a PR whose
    body binds an issue GitHub has not indexed yet. Deduplicated, sorted.
    """
    refs = []
    for ref in pr.get("closingIssuesReferences") or []:
        number = (ref or {}).get("number")
        if isinstance(number, int):
            refs.append(number)
    try:
        encoded = _implemented_issue(str(pr.get("headRefName") or ""))
    except Exception:  # a malformed branch must never kill the sweep
        encoded = None
    if encoded is not None:
        refs.append(int(encoded))
    return sorted(set(refs))


#: The wording a draft verdict carries. READY is the fleet's rule, so the refusal names it.
DRAFT_REASON = ("DRAFT with a bound issue — a fleet PR goes up READY FOR REVIEW, never "
                "draft (owner directive 2026-11-24, issue #1563)")


def draft_findings(prs: list[dict]) -> list[dict]:
    """The DRAFT PRs that carry a bound issue — the ready-for-review verdict (#1563).

    Pure on purpose (rule 6d), the same shape `findings` has: a draft is deliberately NOT a
    "silent PR" (`findings` skips drafts, and `auto_merge_rebase.classify` still answers
    `draft`), but a draft that binds an issue is work the board cannot see or land. Each row
    names the PR, its head, the bound issue(s) and the one remedy.
    """
    out = []
    for pr in prs:
        if not pr.get("isDraft"):
            continue
        issues = bound_issues(pr)
        if not issues:
            continue  # an unfinished draft binds no issue — report status, do not open a PR
        out.append({"number": pr.get("number"), "head": pr.get("headRefName"),
                    "title": (pr.get("title") or "")[:70],
                    "issues": issues, "reasons": [DRAFT_REASON]})
    return out


def rebase_plan(prs: list[dict]) -> list[dict]:
    """Which open non-draft PRs the rebaser may rewrite, and which it must not (rule 6d:
    the DECISION is pure; the git execution below only follows it).

    A CONFLICTING bot PR is NEVER auto-rebased — resolving a conflict belongs to the PR's
    own fix loop or a human (issue #818 Done-when: "a conflicted one is never rewritten").
    A PR owned by a human is never rewritten either, whatever its branch is called (#1295);
    bot ownership comes from `author.is_bot`, with the prefix only a fallback.
    """
    plan = []
    for pr in prs:
        if pr.get("isDraft"):
            continue
        head = str(pr.get("headRefName") or "")
        if not is_bot_owned(pr):
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


def approval_hold(total_runs: int, held_runs: int) -> bool:
    """True when a head commit HAS runs and EVERY one of them is `action_required` (issue #1123).

    The runs exist and executed nothing: GitHub held the branch's own workflows for approval.
    It is its own reason — never "no check runs" (there ARE runs) and never a conflict."""
    return total_runs > 0 and held_runs == total_runs


def findings(prs: list[dict], runs_for: dict[int, int],
             holds_for: dict[int, int] | None = None) -> list[dict]:
    """The SILENT open PRs, from the PR list and a {pr number: check-run count} map.

    Pure on purpose (rule 6d): the decision is testable without a network, and the three reasons
    are kept apart — a conflicting PR cannot run anything; a PR with no runs and no
    conflict is a pipeline that never started (a renamed workflow, a disabled Actions tab);
    and a head whose EVERY run is `action_required` is GitHub holding the branch's own
    workflows for approval (issue #1123) — the runs exist and executed nothing.
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
        number = int(pr.get("number") or 0)
        total = runs_for.get(number, 0)
        if not total:
            reasons.append("no check runs on its head commit")
        elif approval_hold(total, (holds_for or {}).get(number, 0)):
            reasons.append(APPROVAL_HOLD_REASON)
        if reasons:
            out.append({"number": pr.get("number"), "head": pr.get("headRefName"),
                        "title": (pr.get("title") or "")[:70], "reasons": reasons})
    return out


def comment_body(f: dict) -> str:
    lines = [f"<!-- {MARKER} -->", "**This pull request is silent** (issue #442):", ""]
    lines += [f"- {r}" for r in f["reasons"]]
    if any(APPROVAL_HOLD_REASON in r for r in f["reasons"]):
        lines += ["", "GitHub is holding **this PR's own workflows** for approval: the branch "
                      "touches `.github/workflows/`, so a collaborator must approve the pending "
                      "runs before any job executes (Actions tab → the held run → *Review "
                      "pending workflows* → Approve, or `gh api -X POST "
                      "repos/<owner>/<repo>/actions/runs/<run-id>/approvals`). Approving a "
                      "workflow run is a human collaborator's act (rule 6t): the sweep names "
                      "it, never performs it."]
    else:
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


#: The two GENERATED artifacts a bot rebase must land merge-time-current: `OPENSPEC.md`
#: (issue #1049) and `ARCHITECTURE.md`'s §10 inventory block (issue #1601). A rebase whose ONLY
#: unmerged paths are these two is resolved by taking the branch's side and REGENERATING both
#: from the merged tree; any other unmerged path is fix-loop/human work (rule 6s).
GENERATED_REBASE_PATHS = ("OPENSPEC.md", "ARCHITECTURE.md")


def regenerate_index(wt: Path) -> tuple[bool, str]:
    """Regenerate the generated `OPENSPEC.md` ON the rebased tree and commit it (issue #1049).

    A rebase moves the base under the branch's generated index: `OPENSPEC.md` on the branch
    was rendered against the tree at branch-cut time, so a squash of a rebased head would
    still land an index that predates the archives merged since (measured: keepers
    #1038/#1045/#1046/#1047 ping-ponging; rebased bot branches 45fb245/5df9735/28bf765/9a5830a
    red at `openspec-index-check` on 2026-11-16). So every rebase this rebaser lands
    regenerates the index first — through the tree's OWN generator, the same
    `scripts/openspec_index.py --write` `make openspec-index` runs (rule 6d: never a second
    implementation) — and commits it as the agent (rule 3f) BEFORE the lease push. A failed
    regeneration stops the push: the remote branch stays untouched."""
    gen = wt / "scripts" / "openspec_index.py"
    if not gen.is_file():
        return True, ""  # a tree without the generator has no index to regenerate
    r = subprocess.run([sys.executable, str(gen), "--write"], capture_output=True, text=True)
    if r.returncode != 0:
        return False, f"index regeneration failed: {(r.stderr or r.stdout).strip()[:160]}"
    st = _git(wt, "status", "--porcelain", "--", "OPENSPEC.md")
    if not st.stdout.strip():
        return True, ""  # the rebased tree's index was already current
    add = _git(wt, "add", "--", "OPENSPEC.md")
    if add.returncode != 0:
        return False, f"index add failed: {add.stderr.strip()[:120]}"
    c = _git(wt, "commit", "-q",
             "-m", "chore(openspec): regenerate the index on the rebased tree (issue #1049)")
    if c.returncode != 0:
        return False, f"index commit failed: {c.stderr.strip()[:120]}"
    return True, " + OPENSPEC.md regenerated on the rebased tree"


def regenerate_architecture(wt: Path) -> tuple[bool, str]:
    """Regenerate `ARCHITECTURE.md`'s §10 inventory block ON the rebased tree and commit it (#1601).

    The same rebase that moves the index under the branch also moves the description's living block:
    master routinely adds a script, workflow or target while a PR waits, so a head last refreshed at
    branch-cut time lands a block `make architecture-check` refuses (measured 2026-11-24: bot branches
    stalled behind a merge that moved BOTH generated files). So both generated artifacts are
    refreshed through the TREE'S OWN generator — `scripts/architecture_bot.py --write`, the exact
    command `make architecture-refresh` runs (rule 6d: never a second implementation) — and committed
    as the agent (rule 3f) BEFORE the lease push. A failed regeneration stops the push: the remote
    branch stays byte-identical."""
    doc = wt / "ARCHITECTURE.md"
    if not doc.is_file():
        return True, ""  # a tree without the description has no block to refresh
    gen = wt / "scripts" / "architecture_bot.py"
    if not gen.is_file():
        return False, ("ARCHITECTURE.md exists but scripts/architecture_bot.py does not — "
                       "its block cannot be regenerated")
    r = subprocess.run([sys.executable, str(gen), "--write"], capture_output=True, text=True,
                       cwd=str(wt))
    if r.returncode != 0:
        return False, f"architecture regeneration failed: {(r.stderr or r.stdout).strip()[:160]}"
    st = _git(wt, "status", "--porcelain", "--", "ARCHITECTURE.md")
    if not st.stdout.strip():
        return True, ""  # the rebased tree's block was already current
    add = _git(wt, "add", "--", "ARCHITECTURE.md")
    if add.returncode != 0:
        return False, f"architecture add failed: {add.stderr.strip()[:120]}"
    c = _git(wt, "commit", "-q",
             "-m", "chore(architecture): regenerate the inventory block on the rebased tree "
                   "(issue #1601)")
    if c.returncode != 0:
        return False, f"architecture commit failed: {c.stderr.strip()[:120]}"
    return True, " + ARCHITECTURE.md regenerated on the rebased tree"


def _unmerged_paths(wt: Path) -> list[str]:
    """The paths a rebase/merge left unmerged (empty when nothing is)."""
    r = _git(wt, "diff", "--name-only", "--diff-filter=U")
    return [p.strip() for p in r.stdout.splitlines() if p.strip()]


def resolve_generated_conflicts(wt: Path) -> tuple[bool, str]:
    """Resolve a rebase conflict CONFINED to the generated pair, so the rebase can complete.

    Both paths are deterministic outputs of the tree's own generators, so a conflict inside them is
    never a human decision: take the branch's side (the commit being replayed — `--theirs` of a
    rebase; the #583 "keep THE WORK" convention), continue, and let `regenerate_index` /
    `regenerate_architecture` re-derive both from the merged tree. A conflict ANYWHERE ELSE (a
    hand-written file) is returned as a refusal: the caller aborts and the branch stays untouched.

    Returns `(True, "<paths>")` when the rebase continued cleanly, else `(False, reason)`."""
    unmerged = _unmerged_paths(wt)
    if not unmerged:
        return False, "rebase failed with no unmerged paths"
    outside = [p for p in unmerged if p not in GENERATED_REBASE_PATHS]
    if outside:
        return False, ("rebase conflicted outside the generated files "
                       f"({', '.join(outside)}) — branch left untouched (fix-loop/human work)")
    kept: list[str] = []
    for path in unmerged:
        if _git(wt, "checkout", "--theirs", "--", path).returncode != 0:
            return False, (f"could not take the branch's side of {path} — branch left untouched "
                           "(fix-loop/human work)")
        if _git(wt, "add", "--", path).returncode != 0:
            return False, f"could not stage {path} — branch left untouched (fix-loop/human work)"
        kept.append(path)
    # A detached run must never open an editor on the replayed commit's message.
    env = {**os.environ, "GIT_EDITOR": "true"}
    cont = subprocess.run(["git", "-C", str(wt), *_identity_flags(), "rebase", "--continue"],
                          capture_output=True, text=True, env=env)
    if cont.returncode != 0:
        leftover = ", ".join(_unmerged_paths(wt)) or "none"
        return False, (f"rebase --continue failed ({(cont.stderr or cont.stdout).strip()[:120]}); "
                       f"still unmerged: {leftover}")
    return True, ", ".join(kept)


def github_repo_slug(origin_url: str) -> str | None:
    """`owner/name` when the origin is a github.com HTTPS remote, else None (issue #1616).

    The SAME reading `pat_push_url` uses, so the two can never disagree about which remotes are
    GitHub's: a local fixture remote and an ssh remote answer None, and the CI proof below is
    skipped for them — there is no GitHub run to read.
    """
    m = re.match(r"^https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$",
                 str(origin_url or "").strip(), re.I)
    return f"{m.group(1)}/{m.group(2)}" if m else None


def pat_push_url(origin_url: str, pat: str) -> str | None:
    """Rewrite a github.com HTTPS origin into an owner-PAT-authenticated push URL
    (issue #1115). Returns None when the PAT is empty or the origin is not a
    github.com HTTPS URL — a local fixture remote or an ssh remote is NEVER rewritten,
    so the seam cannot silently redirect a push somewhere unverified."""
    if not pat:
        return None
    slug = github_repo_slug(origin_url)
    return f"https://oauth2:{pat}@github.com/{slug}.git" if slug else None


def _ci_gh_json(argv: list[str], expect: str):
    """One gh read for the CI proof (rule 6d): the argv is validated against the ONE field
    contract BEFORE gh runs (issue #1158), and the ANSWER's shape is checked too — gh answers
    `run list --json …` with an ARRAY and `run view --json jobs` with `{"jobs": […]}`. A wrong
    shape is a loud failure, never a silent `[]` that would read as "no jobs scheduled"."""
    problems = gh_json_fields.check_argv(argv)
    if problems:
        raise RuntimeError("gh --json asks for a field gh cannot answer: "
                           + "; ".join(problems) + " (scripts/gh_json_fields.py, issue #1158)")
    try:
        r = subprocess.run(["gh", *argv], capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError(f"gh is not runnable: {exc}") from exc
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(argv[:2])} failed: {r.stderr.strip()[:200]}")
    data = json.loads(r.stdout or "null")
    if expect == "array":
        if isinstance(data, list):
            return data
        raise RuntimeError(f"gh {' '.join(argv[:2])} answered {type(data).__name__}, "
                           "not the array the CI proof reads")
    if isinstance(data, dict) and isinstance(data.get(expect), list):
        return data[expect]
    raise RuntimeError(f"gh {' '.join(argv[:2])} answered no '{expect}' array "
                       f"(got {type(data).__name__})")


def verify_rebased_ci(repo: str, head: str, head_sha: str, *,
                      wait_seconds: int = CI_VERIFY_WAIT_SECONDS) -> tuple[bool, str]:
    """True ONLY when the pushed head's OWN qa-validate run carries >0 jobs (issue #1616).

    The #1115 ghost, measured again on 2026-11-24 (PR #1607 run 45419443908, PR #1608 run
    45419383942): a rebase push under a credential GitHub will not start jobs for leaves the
    branch's newest run `action_required` with ZERO jobs. Pushing through the owner PAT is the
    fix; READING the new head's run back is the PROOF — a green log line is not evidence.

    Polls for a bounded `wait_seconds` (the scheduler is usually seconds behind the push), then
    answers False with the reason: a matched run with zero jobs (the ghost), a matched run whose
    jobs could not be read, or no run for this exact sha at all (`UNPROVEN`). Never True on a
    guess, and never on a DIFFERENT sha's run — a stale head's green run must not vouch for the
    rebased one.
    """
    deadline = time.monotonic() + max(0, int(wait_seconds))
    pending = ""
    while True:
        try:
            runs = _ci_gh_json(
                ["run", "list", "--repo", repo, "--workflow", QA_VALIDATE_WORKFLOW,
                 "--branch", head, "--limit", "20", "--json", _CI_RUN_FIELDS],
                expect="array")
        except (RuntimeError, ValueError) as exc:
            pending = f"could not read the run list ({exc})"
        else:
            match = next((r for r in runs if str(r.get("headSha") or "") == str(head_sha)), None)
            if match is None:
                seen = ", ".join(str(r.get("headSha") or "?")[:12] for r in runs[:3]) or "none"
                pending = (f"no {QA_VALIDATE_WORKFLOW} run for {str(head_sha)[:12]} yet "
                           f"(newest on the branch: {seen})")
            else:
                run_id = match.get("databaseId")
                try:
                    jobs = _ci_gh_json(
                        ["run", "view", str(run_id), "--repo", repo, "--json", _CI_JOBS_FIELDS],
                        expect="jobs")
                except (RuntimeError, ValueError) as exc:
                    return False, (f"run {run_id} on {str(head_sha)[:12]} was found but its jobs "
                                   f"could not be read ({exc}) — CI scheduling is UNPROVEN")
                if jobs:
                    return True, (f"{QA_VALIDATE_WORKFLOW} run {run_id} on "
                                  f"{str(head_sha)[:12]} carries {len(jobs)} job(s)")
                return False, (f"{QA_VALIDATE_WORKFLOW} run {run_id} on {str(head_sha)[:12]} "
                               f"carries ZERO jobs "
                               f"({match.get('conclusion') or match.get('status')}) — the #1115 "
                               "ghost: nothing scheduled the merge gate")
        if time.monotonic() >= deadline:
            return False, f"{pending} after {max(0, int(wait_seconds))}s — CI scheduling is UNPROVEN"
        time.sleep(CI_VERIFY_INTERVAL_SECONDS)


def rebase_and_push(cwd: Path, head: str) -> tuple[bool, bool | None, str]:
    """Rebase origin/<head> onto origin/master in a scratch worktree and push it back to
    the PR's own HEAD branch (rule 6r: push to the PR's head, which re-triggers its CI).

    The scratch worktree keeps the checkout untouched; a conflict ABORTS the rebase and the
    branch is left byte-identical — the rebaser never force-pushes a conflicted result. A
    CLEAN rebase regenerates BOTH generated artifacts on the rebased tree before the push
    (issue #1049 for `OPENSPEC.md`, issue #1601 for `ARCHITECTURE.md`'s block: the shared
    rebaser `pr_health.rebase_and_push` does both, so the weekly sweep and qa-validate's
    `auto-merge` gate can never disagree), and a conflict CONFINED to those two generated
    paths is resolved by regeneration instead of stalling the branch.

    Returns `(pushed, ci_verified, message)`. `ci_verified` is None when the origin is not a
    github.com remote (a local fixture — there is no GitHub run to read); otherwise it is the
    `verify_rebased_ci` verdict on the PUSHED sha (issue #1616): True only when that exact
    head's qa-validate run carries >0 jobs. A push that landed but did not schedule real CI is
    reported as `pushed=True, ci_verified=False` — never as a clean rebase."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        wt = Path(td) / "wt"
        add = _git(cwd, "worktree", "add", "--detach", str(wt), f"refs/remotes/origin/{head}")
        if add.returncode != 0:
            return False, None, f"worktree add failed: {add.stderr.strip()[:120]}"
        try:
            rb = _git(wt, "rebase", "refs/remotes/origin/master")
            resolved = ""
            if rb.returncode != 0:
                ok, note = resolve_generated_conflicts(wt)
                if not ok:
                    _git(wt, "rebase", "--abort")
                    return False, None, note
                resolved = note
            regen_ok, regen_note = regenerate_index(wt)
            if not regen_ok:
                return False, None, f"{regen_note} — branch left untouched (nothing was pushed)"
            arch_ok, arch_note = regenerate_architecture(wt)
            if not arch_ok:
                return False, None, f"{arch_note} — branch left untouched (nothing was pushed)"
            # A rebase REWRITES the branch history, so the push must be a lease push:
            # --force-with-lease pinned to the remote tip THIS run just fetched. If anyone
            # moved the branch since the fetch, the lease fails and nothing is overwritten.
            lease = _git(cwd, "rev-parse", f"refs/remotes/origin/{head}").stdout.strip()
            # The RAW configured URL, not `remote get-url`: git applies insteadOf rewrites
            # to get-url's output, which would hide a github origin behind a transport alias.
            origin_cfg = _git(cwd, "config", "--get", "remote.origin.url").stdout.strip()
            # (issue #1115) THE PUSH CARRIES THE OWNER PAT IDENTITY when the CI step provided
            # one. Measured ghost runs (runs/43839409260, 43839409495, 44004650575): this push,
            # done under the job-token checkout credential, left the resulting PR `pull_request`
            # runs `action_required` with ZERO jobs — the owner sees `no checks reported`,
            # auto-merge is UNSTABLE forever, and qa-validate never runs at all. When
            # GIT_PUSH_PAT is set (the qa-validate auto-merge-rebase step and the pr-health
            # sweep step both provide it), the github.com origin is pushed through an
            # owner-PAT-authenticated URL — the credential class every landed rebase in this
            # repo demonstrably used. A non-github origin (a local fixture remote) is never
            # rewritten: the lease push stays on `origin`.
            push_target, push_identity = "origin", "checkout-credential"
            pat = (os.environ.get("GIT_PUSH_PAT") or "").strip()
            if pat:
                rewritten = pat_push_url(origin_cfg, pat)
                if rewritten:
                    push_target, push_identity = rewritten, "owner-pat"
            push = _git(wt, "push", f"--force-with-lease=refs/heads/{head}:{lease}",
                        push_target, f"HEAD:refs/heads/{head}")
            if push.returncode != 0:
                err = push.stderr.strip()[:120]
                if pat:
                    err = err.replace(pat, "***")  # rule 3d: the token never reaches a log
                return False, None, f"push failed: {err}"
            note = ""
            if resolved:
                note = f" (resolved the generated conflict in {resolved})"
            msg = ("rebased onto origin/master and pushed to the PR head" + note
                   + regen_note + arch_note + f" (push identity: {push_identity})")
            # (issue #1616) THE PROOF: a pushed head is only a landed rebase when its OWN
            # qa-validate run carries jobs. Read it back from GitHub through the ONE gh field
            # contract; skipped for a non-github origin (a fixture has no run to read).
            slug = github_repo_slug(origin_cfg)
            if slug is None:
                return True, None, msg
            pushed_sha = _git(wt, "rev-parse", "HEAD").stdout.strip()
            ci_ok, ci_note = verify_rebased_ci(slug, head, pushed_sha)
            return True, ci_ok, f"{msg}; {ci_note}"
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
            pushed, ci_verified, msg = rebase_and_push(cwd, step["head"])
            if pushed and ci_verified is False:
                # (issue #1616) the branch MOVED but its own qa-validate run carries no jobs —
                # say so plainly instead of reporting a clean `REBASED:` the PR cannot rely on.
                outcomes.append({**step, "done": f"REBASED but CI UNVERIFIED: {msg}",
                                 "ci_verified": False})
            elif pushed:
                outcomes.append({**step, "done": f"REBASED: {msg}", "ci_verified": True})
            else:
                outcomes.append({**step, "done": "kept: " + msg})
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
    resolution belongs to the PR's own fix loop or a human). The remedy names the branch
    worktree as the invocation dir (issue #1335): `base-rebase` reads HEAD from the caller's
    checkout, so a remedy run from the shared `master` clone is a silent no-op."""
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
             f"- `make worktree-resume BRANCH={o['head']}`, then `cd <worktree for {o['head']}>` — "
             "run the next command FROM THE BRANCH WORKTREE, not the shared `master` clone: "
             "`base-rebase` reads HEAD from its invocation directory, so from the wrong "
             "checkout it reports `up-to-date` for a behind branch (issue #1330).",
             f"- From that worktree: `make base-rebase BRANCH={o['head']}` onto the fetched tip — a conflict aborts "
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
    ap.add_argument("--draft-only", action="store_true",
                    help="exit 1 ONLY when a DRAFT PR carries a bound issue — the "
                         "ready-for-review verdict (owner directive 2026-11-24, issue #1563); "
                         "the silent-PR half is skipped")
    ap.add_argument("--dir", default=None,
                    help="checkout to run the git half in (default: current directory)")
    args = ap.parse_args()

    repo_args = ["--repo", args.repo] if args.repo else []
    try:
        prs = _gh_json(["pr", "list", "--state", "open", "--limit", "100", *repo_args,
                        "--json", "number,title,headRefName,isDraft,mergeable,mergeStateStatus,"
                                  "headRefOid,author,closingIssuesReferences"]) or []
        runs_for = {}
        holds_for = {}
        for pr in prs:
            if pr.get("isDraft"):
                continue
            oid = pr.get("headRefOid")
            runs = _gh_json(["run", "list", "--commit", str(oid), "--limit", "100",
                             *repo_args, "--json", "databaseId,conclusion"]) or []
            number = int(pr.get("number") or 0)
            runs_for[number] = len(runs)
            # issue #1123: runs GitHub HELD for approval executed no jobs.
            holds_for[number] = sum(1 for r in runs
                                    if str(r.get("conclusion") or "").lower() == "action_required")
    except (RuntimeError, ValueError) as exc:
        print(f"[pr-health] FAIL: {exc}", file=sys.stderr)
        return 2

    # THE DRAFT VERDICT (issue #1563): reported in BOTH modes. It never changes a PR; it only
    # NAMES a draft that carries a bound issue, with the issue number, because a draft is
    # invisible to reviewers and to `auto-merge` and silently stalls the board. `findings`
    # deliberately skips drafts, and `auto_merge_rebase.classify` still answers `draft` — both
    # untouched, so this is additive and no existing verdict changes meaning.
    drafts = draft_findings(prs)
    print(f"[pr-health] {len(drafts)} draft PR(s) with a bound issue (must be READY, never draft)")
    for d in drafts:
        issues = ", ".join(f"#{n}" for n in d["issues"])
        print(f"  DRAFT #{d['number']} {d['head']} bound to {issues}: {DRAFT_REASON}")

    if args.draft_only:
        # The CI assertion mode: a bound draft is a RED gate, nothing else is. No rebasing,
        # no silent-PR verdict, no comments — this is the smallest suitable CI-side assertion.
        return 1 if drafts else 0

    silent = findings(prs, runs_for, holds_for)
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
