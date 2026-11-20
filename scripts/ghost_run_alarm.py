#!/usr/bin/env python3
"""Flag every GHOST qa-validate run — a `pull_request` pipeline that COMPLETED with ZERO jobs
(issue #1115).

Measured on the owner's PRs #1100 and #1114 (runs/43839409260, 43839409495, 44004650575): a
`pull_request` qa-validate run concluded `action_required` / `success` carrying NO jobs at all —
`validate`, `live-smoke` and `auto-merge` never ran, `gh pr checks` answered `no checks
reported`, and auto-merge stayed UNSTABLE forever. The pipeline never FAILED; it never RAN. A
branch pushed by a bot under a checkout credential that GitHub will not let start jobs for a
PR is exactly this shape, and no alarm read `pull_request` runs at all: `master-alarm` reads
pushes to master, `queued-alarm` reads queued/in_progress runs, `sweep-alarm` reads
`issue-bot.yml` deliveries. A ghost was invisible to every gate.

This sweep closes the gap queued-alarm.yml's own header names (#450: "Nothing checked whether
a pipeline that OWNS a schedule ever DELIVERED on it — the quietest failure…"): the same
question for a PR pipeline that owns a TRIGGER but produced no jobs.

Read-only (rule 6j's read-only half): it writes nothing and fixes nothing — the remedy is the
#1115 push-identity fix, or a host-side re-push of the head (§6s) so real jobs arrive.

Exit codes: 0 = no ghost, 1 = at least one ghost run (the sweep goes RED instead of staying
quiet), 2 = a GitHub read failed (never a silent clean).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gh_json_fields  # noqa: E402  (the ONE gh --json field contract — rule 6d)

WORKFLOW = "qa-validate.yml"
WINDOW_HOURS_DEFAULT = 168  # a week: every open PR's newest run stays visible to the sweep
# Built through the ONE gh field contract (issue #1158): gh's run link field is `url`, and a
# field gh cannot answer here refuses the BUILD of this alarm instead of its read.
RUNS_JSON = gh_json_fields.request(
    "run list",
    "databaseId,workflowName,name,headBranch,headSha,status,conclusion,createdAt,url",
)


def _gh_json(repo: str, *args: str, expect: str = "array") -> list:
    """One seam for the alarm's gh reads (rule 6d): the argv is validated against the field
    contract BEFORE gh is called (issue #1158), and the ANSWER's shape is checked too. gh answers
    `run list --json …` with an ARRAY and `run view --json jobs` with an OBJECT `{"jobs": […]}`;
    an answer that is neither is a loud failure, never a silent `[]` that makes every run look
    like a ghost."""
    problems = gh_json_fields.check_argv(list(args))
    if problems:
        raise RuntimeError("gh --json asks for a field gh cannot answer: "
                           + "; ".join(problems) + " (scripts/gh_json_fields.py, issue #1158)")
    try:
        r = subprocess.run(["gh", *args, "--repo", repo], capture_output=True, text=True)
    except FileNotFoundError as exc:
        # A missing `gh` is a failed READ (exit 2, READ FAILED), never a traceback on the sweep.
        raise RuntimeError(f"gh is not runnable: {exc}") from exc
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])} failed: {r.stderr.strip()[:200]}")
    data = json.loads(r.stdout)
    if not isinstance(data, (list, dict)):
        raise RuntimeError(f"gh {' '.join(args[:2])} answered "
                           f"{type(data).__name__}, not JSON the alarm can read")
    if expect == "array":
        if isinstance(data, list):
            return data
        raise RuntimeError(f"gh {' '.join(args[:2])} answered a "
                           f"{type(data).__name__}, not the array the alarm reads")
    if isinstance(data, dict) and isinstance(data.get(expect), list):
        return data[expect]
    raise RuntimeError(f"gh {' '.join(args[:2])} answered no '{expect}' array "
                       f"(got {type(data).__name__})")


def recent_pr_runs(repo: str, workflow: str = WORKFLOW, limit: int = 50) -> list[dict]:
    return _gh_json(repo, "run", "list", "--workflow", workflow, "--event", "pull_request",
                    "--limit", str(limit), "--json", RUNS_JSON)


def jobs_of(repo: str, run_id) -> list[dict]:
    return _gh_json(repo, "run", "view", str(run_id), "--json", "jobs", expect="jobs")


def ghost_verdict(run: dict, jobs: list) -> bool:
    """The DECISION, pure (rule 6d): a COMPLETED pull_request run is a ghost when GitHub
    waited for an action nobody can take (conclusion `action_required`) or when it concluded
    without running a single job. A skipped run is GitHub's own skip (concurrency), not a
    ghost; an in-flight run belongs to `queued-alarm`, not here."""
    if run.get("status") != "completed":
        return False
    if run.get("conclusion") == "skipped":
        return False
    return run.get("conclusion") == "action_required" or len(jobs) == 0


def ghosts(repo: str, *, workflow: str = WORKFLOW, window_hours: int = WINDOW_HOURS_DEFAULT,
           limit: int = 50, now: dt.datetime | None = None) -> list[dict]:
    now = now or dt.datetime.now(dt.timezone.utc)
    out = []
    for run in recent_pr_runs(repo, workflow, limit):
        created = (run.get("createdAt") or "").replace("Z", "+00:00")
        try:
            age_h = (now - dt.datetime.fromisoformat(created)).total_seconds() / 3600.0
        except ValueError:
            age_h = 0.0  # unreadable timestamp: keep the run visible, never hide it
        if age_h > window_hours:
            continue
        run_id = run.get("databaseId")
        jobs = jobs_of(repo, run_id) if run.get("status") == "completed" else []
        if ghost_verdict(run, jobs):
            out.append({**run, "jobs": len(jobs), "age_hours": round(age_h, 1)})
    return out


def render(rows: list[dict], repo: str, window_hours: int) -> str:
    if not rows:
        return (f"[ghost-run-alarm] OK {repo}: {WORKFLOW} has no ghost runs "
                f"(no completed pull_request run with zero jobs inside {window_hours}h)")
    lines = [f"[ghost-run-alarm] FAIL {repo}: {len(rows)} GHOST {WORKFLOW} run(s) — "
             f"a pull_request pipeline that never ran a single job:"]
    for g in rows:
        lines.append(f"  {g.get('url')} conclusion={g.get('conclusion')} jobs={g['jobs']} "
                     f"head={g.get('headBranch')} age={g['age_hours']}h")
    lines.append("  A ghost means `gh pr checks` says `no checks reported` and auto-merge is "
                 "UNSTABLE: the PR's validation can never arrive. Remedy (issue #1115): re-push "
                 "the head with the owner-PAT identity (`make pr-health REBASE=1` on the host, "
                 "or the qa-validate `auto-merge-rebase` seam) so GitHub starts real jobs.")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", required=True, help="owner/repo to read")
    ap.add_argument("--workflow", default=WORKFLOW)
    ap.add_argument("--window-hours", type=int, default=WINDOW_HOURS_DEFAULT)
    ap.add_argument("--limit", type=int, default=50)
    args = ap.parse_args()
    try:
        rows = ghosts(args.repo, workflow=args.workflow, window_hours=args.window_hours,
                      limit=args.limit)
    except (RuntimeError, json.JSONDecodeError) as exc:
        print(f"[ghost-run-alarm] READ FAILED (exit 2, never a silent clean): {exc}")
        return 2
    print(render(rows, args.repo, args.window_hours))
    return 1 if rows else 0


if __name__ == "__main__":
    sys.exit(main())
