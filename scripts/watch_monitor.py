#!/usr/bin/env python3
"""Deterministic change detector for the tll issue/PR/CI watcher (issue #1266).

One agent job must not wake every tick just because a clock moved. This script emits ONLY
changed markers, with no timestamps and no random ordering:

    C:<comment id>                       a new issue/PR comment
    R:<run id>:<status>:<conclusion>[:<workflow>][:<pr>]  a CI run changed state
    G:<run id>:<pr>                      a GHOST PR run: completed with zero jobs (#1797)
    M:<master sha>                       master moved (a merge or a push)
    H:<bucket>                           opt-in work heartbeat (--heartbeat-seconds N)
    S:<issue>:<claim-id>:stale|released  a claim became stale / was released (#1620)

An `R:` marker names its PR when the run has one (issue #1284), so a woken lane can read
that PR's own thread before acting instead of guessing which thread a run id belongs to. A
push-triggered run carries no `pull_requests` and keeps the shorter shape.

A `G:` marker is the board-visible half of issue #1797: a zero-job `action_required` run on
an open PR used to sit UNSTABLE with no issue and no `R:` duty (rule 6w files only concluded
`failure`), so neither host could tell "never started" from "slow". The ghost decision is the
ONE in `ghost_run_alarm.ghost_verdict` (rule 6d); the marker carries the PR identity, fires
once per run, and points the lane at the owner-identity re-push remedy in `ghost_run_alarm`.

GitHub CLEARS a run's `pull_requests` once its PR merges and the branch is deleted (measured
2026-11-23: run `45085274450` on the merged PR #1350's old head answered `pull_requests: []`
while `event=pull_request`), so a marker emitted after the merge would lose the PR field the
lane needs. The caller-owned state therefore also carries a `run_prs` map: a run's PR is
recorded the first time it is seen with a non-empty `pull_requests`, and reused on later ticks
when the association has been cleared. The marker's shape never changes — a push run still
emits the shorter form, and a PR run keeps its trailing `:<pr>`.

The map only helps a run that was SEEN while its PR was open. A red run whose FIRST sight is
after the merge (auto-merge lands a PR minutes after the run concludes, and the detector ticks
every few minutes) has no recorded PR and no live association, so the marker loses the field
anyway. Measured 2026-11-23: `R:45116060775:completed:failure:qa-validate` on merged PR #1362's
old head, with `run_prs: {}` in the caller's state. Such a run is therefore resolved from a
merge-surviving source — `head_branch` → `gh pr list --state all --head <branch>`, which keeps
answering after the branch is deleted — before the diff runs. That resolution is capped
(`PR_RESOLVE_MAX`) so a tick with many merged PR runs cannot become a request storm.

With no heartbeat flag the quiet tick is still silent. The heartbeat is a bucket of
wall-clock time divided by N, never a timestamp, so identical ticks look identical to
the caller's state file and only the bucket boundary wakes the agent.

Comment fetch asks GitHub for newest-first (`sort=created&direction=desc`, issue #1360): the
`/issues/comments` endpoint defaults to oldest-first, so a plain `per_page=100` pinned both
hosts' cursors at the 100th-oldest comment and no later comment could ever emit `C:`. A
one-time `comments_v2` cursor migration baselines the repaired detector without waking a
lane with the whole stale backlog on its first repaired tick.

The JSON state file belongs to the caller's scratch home, never to the repository. The
external `gh` CLI is the only stand-in a test needs; the request-building and diffing code
here is the real product.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from ghost_run_alarm import ghost_verdict  # noqa: E402  (scripts/ is on sys.path; ONE ghost decision, rule 6d)

DEFAULT_REPO = "andyholst/trending-local-llms"
MARKER_PREFIXES = ("C:", "R:", "G:", "M:", "H:", "S:")

# The per-tick cap on job reads for ghost detection (issue #1797). A ghost is a COMPLETED
# `action_required` run, so only those runs need a jobs read; an unreadable one contributes
# no jobs entry and therefore no G marker, never a guess that wakes both hosts.
GHOST_JOBS_MAX = 10

# The per-tick cap on branch→PR resolutions (issue #1364). A tick that follows a burst of
# merges can carry many PR runs whose `pull_requests` GitHub has already cleared; resolving
# every one with a `gh pr list` call would turn the detector into a request storm, so the
# oldest-first budget bounds the tick and the rest resolve on a later tick.
PR_RESOLVE_MAX = 10

# The minimum settle window between a wake-up and a claim, in seconds (issue #1312).
#
# The watcher is deliberately timestamp-free, so it cannot filter a marker by age; the
# window is the floor the WOKEN lane applies before it claims, and this constant is the
# ONE place the number lives — `AGENTS.md` §7b names it and `make watch-monitor --check`
# refuses a weaker floor, so neither the rulebook row nor the pin can be dropped silently.
CLAIM_SETTLE_SECONDS = 180
CLAIM_SETTLE_FLOOR_SECONDS = 60

# The comment fetch must be explicitly newest-first (issue #1360). GitHub answers
# `/issues/comments?per_page=100` oldest-first by default, which froze the cursor at the
# 100th-oldest comment. One seam, so the request and its guard cannot disagree.
COMMENT_QUERY = "comments?per_page=100&sort=created&direction=desc"
COMMENTS_V2_KEY = "comments_v2"


def heartbeat_marker(interval_seconds: int, now: float | None = None) -> str | None:
    """Deterministic opt-in work heartbeat: one H marker per interval bucket."""
    if interval_seconds <= 0:
        return None
    tick = int(time.time() if now is None else now) // interval_seconds
    return f"H:{tick}"


def as_list(value: object) -> list[dict]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def workflow_token(name: object) -> str:
    """A workflow name as one colon-free, single-line marker field (issue #1288).

    `actions/runs` rows carry `name`. Adding it lets a fleet reader tell a
    guard/closure-only `success` from a full `qa-validate` `success` without a
    second call. Colons and line breaks are dropped so one token is one field and
    one marker stays one line; a missing/blank name contributes no field at all.
    """
    if not isinstance(name, str):
        return ""
    return "".join(ch for ch in name if ch.isprintable() and ch not in ":\r\n")


def pull_token(run: dict) -> str:
    """The pull-request number this run belongs to, as one marker field (issue #1284).

    `actions/runs` rows carry `pull_requests` for a PR-triggered run and an empty list for a
    push. Returning "" keeps the marker's existing shape for a push, so no recorded marker
    and no reader changes; a non-int entry contributes nothing rather than a malformed field.
    """
    rows = run.get("pull_requests")
    if not isinstance(rows, list) or not rows:
        return ""
    number = rows[0].get("number") if isinstance(rows[0], dict) else None
    return str(number) if isinstance(number, int) and not isinstance(number, bool) else ""


def resolve_branch_prs(repo: str, client: str, branches: list[str]) -> dict[str, int]:
    """Map `head_branch` → PR number for branches whose run row lost `pull_requests` (#1364).

    `gh pr list --state all --head <branch>` keeps answering after the PR merges and its branch
    is deleted (measured 2026-11-23: PR #1362, merged `2d5b1be`, branch gone, still resolves), so
    it is the merge-surviving source issue #1355's Done-when named. A branch with no unique PR
    contributes nothing rather than a guess; a failed read contributes nothing either, so one
    unreadable branch can never lose the rest of the tick's markers.
    """
    resolved: dict[str, int] = {}
    for branch in branches[:PR_RESOLVE_MAX]:
        proc = subprocess.run(
            [client, "pr", "list", "--repo", repo, "--state", "all",
             "--head", branch, "--json", "number", "--limit", "1"],
            capture_output=True, text=True, timeout=40, check=False)
        if proc.returncode != 0:
            continue
        try:
            rows = json.loads(proc.stdout)
        except ValueError:
            continue
        if isinstance(rows, list) and len(rows) == 1 and isinstance(rows[0].get("number"), int):
            resolved[branch] = rows[0]["number"]
    return resolved


def inject_run_prs(runs: list[dict], pr_by_branch: dict[str, int]) -> list[dict]:
    """Pure half of the #1364 resolution: give a PR run back the `pull_requests` the merge cleared.

    Only a `pull_request` run whose live `pull_requests` is empty and whose `head_branch` the
    caller resolved is touched, so a push run and a run that still carries its association are
    passed through byte-identically and the marker's shape never changes. The diff
    (`marker_state`) stays pure; this is the only place the resolved number enters a run row.
    """
    injected: list[dict] = []
    for run in runs:
        branch = run.get("head_branch")
        if (run.get("event") == "pull_request" and not pull_token(run)
                and isinstance(branch, str) and branch in pr_by_branch):
            run = {**run, "pull_requests": [{"number": pr_by_branch[branch]}]}
        injected.append(run)
    return injected


def marker_state(previous: dict, payload: dict, heartbeat_seconds: int = 0,
                 now: float | None = None) -> tuple[list[str], dict]:
    """Pure diff: return sorted markers and the NEXT state for one snapshot.

    `payload` is exactly what the gh calls returned: `comments` maps `issues`/`pulls` to
    comment rows, `runs` is a list of workflow-run rows, `master` is a commit object.
    An opt-in heartbeat adds one deterministic H marker without storing a clock.
    """
    if not isinstance(previous, dict):
        previous = {}
    lines: list[str] = []
    raw_run_prs = previous.get("run_prs")
    prev_run_prs: dict = raw_run_prs if isinstance(raw_run_prs, dict) else {}
    migrated = previous.get(COMMENTS_V2_KEY) is True
    state: dict = {"comments": {}, "runs": {}, "master": previous.get("master"),
                   "run_prs": {str(k): str(v) for k, v in prev_run_prs.items()},
                   COMMENTS_V2_KEY: True}

    prev_comments = previous.get("comments", {}) if isinstance(previous.get("comments"), dict) else {}
    for kind in ("issues", "pulls"):
        rows = as_list(payload.get("comments", {}).get(kind, [])) if isinstance(payload.get("comments"), dict) else []
        ids = [int(r["id"]) for r in rows if isinstance(r.get("id"), int)]
        seen = int(prev_comments.get(kind, 0)) if str(prev_comments.get(kind, 0)).isdigit() else 0
        if migrated:
            for comment_id in sorted(i for i in ids if i > seen):
                lines.append(f"C:{comment_id}")
        # On the first tick after the newest-first repair the stale cursor is seeded to
        # the newest comment instead of waking the lane with ~100 stale C markers (#1360).
        state["comments"][kind] = max([seen] + ids) if ids else seen

    prev_runs = previous.get("runs", {}) if isinstance(previous.get("runs"), dict) else {}
    raw_ghosts = previous.get("ghosts")
    prev_ghosts: dict = raw_ghosts if isinstance(raw_ghosts, dict) else {}
    state["ghosts"] = {str(k): str(v) for k, v in prev_ghosts.items()}
    raw_jobs = payload.get("jobs")
    jobs_by_run: dict = ({str(k): v for k, v in raw_jobs.items()}
                         if isinstance(raw_jobs, dict) else {})
    for run in as_list(payload.get("runs")):
        run_id = run.get("id")
        if not isinstance(run_id, int):
            continue
        stamp = f"{run.get('status', '?')}:{run.get('conclusion') or '-'}"
        token = workflow_token(run.get("name"))
        if token:
            stamp += f":{token}"
        live_pr = pull_token(run)
        pr = live_pr or prev_run_prs.get(str(run_id), "")
        if live_pr:
            state["run_prs"][str(run_id)] = live_pr
        if pr:
            stamp += f":{pr}"
        state["runs"][str(run_id)] = stamp
        if prev_runs.get(str(run_id)) != stamp:
            lines.append(f"R:{run_id}:{stamp}")
        jobs = jobs_by_run.get(str(run_id))
        # Reuse the alarm's ONE ghost verdict (rule 6d), then narrow to the measured
        # zero-job shape from #1797: an action_required run that DID start has its own
        # duty and must not wake both hosts as a never-started head.
        if isinstance(jobs, list) and not jobs and ghost_verdict(run, jobs):
            state["ghosts"][str(run_id)] = pr or "-"
            # A ghost is board-visible ONCE per run, and only with a PR identity: a lane
            # must be able to name the PR whose head never started (issue #1797).
            if pr and str(run_id) not in prev_ghosts:
                lines.append(f"G:{run_id}:{pr}")

    master = payload.get("master")
    master_sha = master.get("sha") if isinstance(master, dict) else None
    if isinstance(master_sha, str):
        state["master"] = master_sha
        if previous.get("master") != master_sha:
            lines.append(f"M:{master_sha[:12]}")

    heartbeat = heartbeat_marker(heartbeat_seconds, now)
    if heartbeat:
        lines.append(heartbeat)

    if not previous:
        lines.append("BASELINE")
    return sorted(set(lines)), state


def read_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")


def gh_client() -> str:
    return shutil.which("gh") or os.environ.get("TLL_GH", "gh")


def fetch_ghost_jobs(repo: str, client: str, runs: list[dict]) -> dict[str, list]:
    """Read the jobs of completed `action_required` PR runs — the evidence a G marker needs.

    Capped at GHOST_JOBS_MAX so a burst of stuck heads cannot turn one detector tick into a
    request storm; an unreadable run contributes no entry, so the monitor never guesses that
    a PR is blocked (issue #1797). The explicit `client` is the one the caller pinned.
    """
    jobs: dict[str, list] = {}
    targets = [r for r in runs
               if r.get("status") == "completed" and r.get("conclusion") == "action_required"
               and isinstance(r.get("id"), int)][:GHOST_JOBS_MAX]
    for run in targets:
        run_id = run["id"]
        proc = subprocess.run(
            [client, "api", f"repos/{repo}/actions/runs/{run_id}/jobs?per_page=100"],
            capture_output=True, text=True, timeout=40, check=False)
        if proc.returncode != 0:
            continue
        try:
            data = json.loads(proc.stdout)
        except ValueError:
            continue
        rows = data.get("jobs") if isinstance(data, dict) else None
        if isinstance(rows, list):
            jobs[str(run_id)] = rows
    return jobs


def fetch_payload(repo: str, client: str) -> dict:
    def get(path: str) -> object:
        proc = subprocess.run([client, "api", f"repos/{repo}/{path}"],
                              capture_output=True, text=True, timeout=40, check=False)
        if proc.returncode != 0:
            raise RuntimeError("gh api failed")
        try:
            return json.loads(proc.stdout)
        except ValueError as exc:
            raise RuntimeError("gh json failed") from exc

    comments = {}
    for kind in ("issues", "pulls"):
        comments[kind] = as_list(get(f"{kind}/{COMMENT_QUERY}"))
    runs_payload = get("actions/runs?per_page=30")
    runs = as_list(runs_payload.get("workflow_runs")) if isinstance(runs_payload, dict) else as_list(runs_payload)
    # A PR run whose FIRST sight is after its merge has neither a live `pull_requests` nor a
    # recorded one (issue #1364): resolve those branches from the merge-surviving source before
    # the diff, so the marker still names the thread the woken lane must read.
    missing: list[str] = []
    for run in runs:
        branch = run.get("head_branch")
        if (run.get("event") == "pull_request" and not pull_token(run)
                and isinstance(branch, str) and branch and branch not in missing):
            missing.append(branch)
    if missing:
        # Keep the caller's gh (the explicit --gh path in the stripped cron env): a second
        # gh_client() lookup here would silently drop it for the resolution leg.
        runs = inject_run_prs(runs, resolve_branch_prs(repo, client, missing))
    return {"comments": comments, "runs": runs, "master": get("commits/master"),
            "jobs": fetch_ghost_jobs(repo, client, runs)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=os.environ.get("TLL_REPO", DEFAULT_REPO))
    ap.add_argument("--state", default=os.environ.get("TLL_WATCH_STATE", ""))
    ap.add_argument("--gh", default=None, help="explicit gh path for stripped cron environments")
    ap.add_argument("--check", action="store_true", help="offline contract check; no network, no state write")
    ap.add_argument("--claim-settle-seconds", type=int, default=CLAIM_SETTLE_SECONDS,
                    dest="claim_settle_seconds",
                    help="the settle window a caller applies before claiming "
                         f"(default {CLAIM_SETTLE_SECONDS}s, floor {CLAIM_SETTLE_FLOOR_SECONDS}s)")
    ap.add_argument("--heartbeat-seconds", type=int, default=0,
                    dest="heartbeat_seconds",
                    help="opt-in deterministic H marker every N seconds (0 disables)")
    args = ap.parse_args(argv)

    if args.check:
        if not all(m in MARKER_PREFIXES for m in ("C:", "R:", "G:", "M:", "H:", "S:")):
            print("CHECK FAILED: marker prefixes changed", file=sys.stderr)
            return 2
        if ghost_verdict({"status": "completed", "conclusion": "action_required"}, []) is not True:
            print("CHECK FAILED: the ghost decision drifted from ghost_run_alarm", file=sys.stderr)
            return 2
        if args.claim_settle_seconds < CLAIM_SETTLE_FLOOR_SECONDS:
            print(f"CHECK FAILED: the claim settle window {args.claim_settle_seconds}s is below "
                  f"the {CLAIM_SETTLE_FLOOR_SECONDS}s floor", file=sys.stderr)
            return 2
        print(f"[watch-monitor] OK: C/R/G/M/H/S markers, caller-owned state, no timestamps; "
              f"claim settle window {args.claim_settle_seconds}s "
              f"(floor {CLAIM_SETTLE_FLOOR_SECONDS}s)")
        return 0

    state_path = Path(args.state) if args.state else None
    if state_path is None:
        print("REFUSED: --state is required for a live run (use --check offline)", file=sys.stderr)
        return 2
    try:
        state_path.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        pass
    else:
        print("REFUSED: --state must live outside the repository", file=sys.stderr)
        return 2

    try:
        payload = fetch_payload(args.repo, args.gh or gh_client())
    except Exception as exc:
        # Stable, secret-free token: a repeated failure every tick does not wake the agent twice.
        print(f"ERROR:{exc}")
        return 0

    lines, state = marker_state(read_state(state_path), payload, args.heartbeat_seconds)
    write_state(state_path, state)
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
