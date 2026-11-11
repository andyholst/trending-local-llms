#!/usr/bin/env python3
"""The red-master alarm (issue #527): a deterministic gate on a `push` to master has no repairer.

`qa-validate`'s `validate` job runs on a `push` to master as well as on PRs, and every repair
path in this repo needs a PR: `dispatch-fixbot` only touches `ci/trending-refresh-*` /
`ci/data-gap-*` PRs, `fix-bot` resolves a PR and refuses anything else, `pr-health` sweeps open
PRs, and `architecture-bot` repairs exactly two generated files (`ARCHITECTURE.md`, `OPENSPEC.md`
via #526). So when a deterministic gate goes red AFTER `auto-merge` — a stale generated file, a
data invariant broken, a table malformed (measured: run 39625708799, red at the `OpenSpec gate`
with the unit tests never reached) — nothing in the repo opens an edit: master stays red until a
human pastes a run URL into a thread.

This tool is the ALARM half. It reads `qa-validate`'s newest `push`-to-master run and, when it
concluded in failure, exits 1 naming the run URL and the failing job — so the scheduled sweep
that calls it goes RED in the Actions tab instead of staying quiet (the `queued-alarm` /
`bot-health` model: a red state must produce a signal, not a page nobody opens). It never writes
anything; the KEEPER half for the one repair path that exists (architecture-bot regenerates
`ARCHITECTURE.md` and `OPENSPEC.md`) is documented beside the registry below.

The KEEPER/ALARM registry is the TABLE the issue demands, and `tests/test_master_alarm.py` fails
when a new gate is added to the `validate` job without landing on one of the two lists.

Usage:
    python3 scripts/master_alarm.py --repo OWNER/NAME [--limit N]

Exit: 0 = the newest push-to-master run is green (or pending) and no alarm is owed; 1 = it is
red, naming the run URL and the failing jobs; 2 = the GitHub read failed (a tool that cannot read
must not report a pass).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

WORKFLOW = "qa-validate.yml"
HEAD_BRANCH = "master"
#: A conclusion that means the run did not do its job (mirrors scripts/bot_health.py::BAD).
BAD = frozenset({"failure", "timed_out", "cancelled", "startup_failure", "action_required"})

# ---------------------------------------------------------------------------
# The KEEPER / ALARM table (issue #527) — every deterministic gate in
# qa-validate's `validate` job, with the thing that stops a red master from
# being silent. A gate is either KEEP (a bot in this repo regenerates the file
# that gate checks) or ALARM (the master-alarm above makes it visible). This is
# the single list; tests/test_master_alarm.py reads it to fail when a gate in
# the validate job is on NEITHER list. Additive only, never a deletion.
# ---------------------------------------------------------------------------
GATES: dict[str, tuple[str, str]] = {
    # -- KEEP — architecture-bot regenerates the artifact the gate checks, so a
    #    merge that leaves the file stale is repaired (hourly on the fleet day).
    "architecture-check": ("keeper", "architecture-bot"),   # regenerates ARCHITECTURE.md (#479)
    "openspec-check": ("keeper", "architecture-bot"),       # regenerates OPENSPEC.md index (#526)
    # -- ALARM — the master-alarm makes a red push-to-master run visible.
    "lint": ("alarm", "master-alarm"),
    "check-commit-authorship": ("alarm", "master-alarm"),
    "pr-closure": ("alarm", "master-alarm"),
    "image-ensure": ("alarm", "master-alarm"),
    "secret-scan": ("alarm", "master-alarm"),
    "secret-scan-self-test": ("alarm", "master-alarm"),
    "check-secret-output": ("alarm", "master-alarm"),
    "action-pin-check": ("alarm", "master-alarm"),
    "nerve-check": ("alarm", "master-alarm"),
    "validate": ("alarm", "master-alarm"),
    "validate-search": ("alarm", "master-alarm"),
    "validate-mapped": ("alarm", "master-alarm"),
    "openspec-archive-check": ("alarm", "master-alarm"),
    "test": ("alarm", "master-alarm"),
}

#: The gates the keeper family (architecture-bot) repairs, by name.
KEEPERS = {g for g, (kind, _) in GATES.items() if kind == "keeper"}
#: The make targets the master-alarm covers (explicit, so a NEW gate that is
#: neither kept nor alarm-covered fails tests/test_master_alarm.py immediately).
ALARMED = {g for g, (kind, _) in GATES.items() if kind == "alarm"}


def _gh(args: list[str]) -> str:
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {out.stderr.strip() or 'non-zero exit'}")
    return out.stdout


def validate_gates_from_trees(wf_text: str) -> list[str]:
    """The `make <target>` gates the given `validate` job runs, in order.

    Used by tests to compare the tree against the registry: a `make X` the validate job
    runs that `GATES` does not name is caught as "a gate in validate on neither list".
    Both shapes count (issue #527): the inline `run: make X` step AND the bare
    `make X` continuation line of a multi-line `run:` block — the first version matched
    only the continuation lines and read the three gates of ONE block as the whole job.
    """
    return re.findall(r"make\s+([a-z0-9_-]+)(?=[\"'\s]|$)", wf_text, re.M)


def unchecked_gates(wf_text: str) -> list[str]:
    """Gates the validate job runs that `GATES` does not cover (the defect, if any)."""
    return sorted(set(validate_gates_from_trees(wf_text)) - set(GATES))


def newest_push_run(repo: str, limit: int = 10) -> dict | None:
    """The newest `push`-to-`master` `qa-validate` run, or None when none exists."""
    raw = _gh(["run", "list", "--workflow", WORKFLOW, "--event", "push",
               "--limit", str(limit), "--json",
               "databaseId,createdAt,conclusion,status,url,headBranch,displayTitle",
               "--repo", repo])
    runs = [r for r in json.loads(raw or "[]") if r.get("headBranch") == HEAD_BRANCH]
    if not runs:
        return None
    runs.sort(key=lambda r: r.get("createdAt") or "", reverse=True)
    return runs[0]


def failing_jobs(repo: str, run_id: int) -> list[str]:
    """Names of the jobs that concluded in failure on the given run (best effort)."""
    try:
        raw = _gh(["run", "view", str(run_id), "--json", "jobs", "--repo", repo])
        jobs = json.loads(raw).get("jobs", [])
        return [j.get("name") or "?" for j in jobs
                if (j.get("conclusion") or "") in BAD]
    except (RuntimeError, ValueError):
        return []


def verdict(repo: str, limit: int = 10) -> tuple[int, str]:
    """The alarm's decision as (exit, message). Pure wrapper over the reads."""
    try:
        run = newest_push_run(repo, limit)
    except (RuntimeError, ValueError) as exc:
        return 2, f"[master-alarm] FAIL: {exc}"
    if run is None:
        return 0, f"[master-alarm] OK: no `push`-to-`{HEAD_BRANCH}` {WORKFLOW} run exists."
    conclusion = (run.get("conclusion") or run.get("status") or "unknown").lower()
    if conclusion == "success":
        at = (run.get("createdAt") or "?").replace("T", " ").replace("Z", "")
        return 0, (f"[master-alarm] OK: newest push-to-master qa-validate run "
                   f"{run.get('databaseId')} is green ({at}).")
    if conclusion in BAD:
        run_id = run.get("databaseId")
        lines = [f"[master-alarm] FAIL: newest push-to-master {WORKFLOW} run {run_id} "
                 f"concluded '{conclusion}'."]
        jfails = failing_jobs(repo, run_id) if run_id is not None else []
        if jfails:
            lines.append("  failing job(s): " + ", ".join(jfails))
        else:
            lines.append("  (the run's failing job could not be read)")
        url = run.get("url") or ""
        if url:
            lines.append(f"  run: {url}")
        lines.append("  master is red and no PR exists to repair it — this is the alarm that "
                     "makes it visible (issue #527).")
        return 1, "\n".join(lines)
    # pending / in_progress / skipped: not a verdict yet, not an alarm.
    return 0, (f"[master-alarm] OK: newest push-to-master run {run.get('databaseId')} is "
               f"{conclusion} — not a failure, nothing to alarm.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Fail when the newest push-to-master qa-validate run is red (issue #527)")
    ap.add_argument("--repo", required=True, help="owner/name")
    ap.add_argument("--limit", type=int, default=10, help="how many push runs to read")
    args = ap.parse_args(argv)
    rc, msg = verdict(args.repo, args.limit)
    print(msg)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
