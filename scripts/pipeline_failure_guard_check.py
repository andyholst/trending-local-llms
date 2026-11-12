#!/usr/bin/env python3
"""The ledger gate: a diagnosed pipeline failure may not close without its guard (issue #802).

`make pipeline-failure-issue` files one issue per failed main-pipeline run and appends the run to
`data/pipeline_failures.json` (append-only, rule 3b). This is the half that keeps the fix honest:
it runs in qa-validate's `validate` job on every PR and push, and it REFUSES:

  * a ledger entry whose issue is CLOSED while the entry names NO fix PR and NO guard test —
    the error class was closed away without anything that fails if it is reintroduced;
  * a ledger entry that names a fix PR but whose `guard` test does not exist as a collected
    module under `tests/` — a guard that was promised and never landed.

An entry whose fix is still IN FLIGHT (open issue, no fix PR yet) is REPORTED, never red — the
gate enforces the closing move, not the opening one. An issue whose state cannot be read (a
transport failure) is indeterminate, never counted as closed (the same rule the link check uses
for 429/5xx).

Exit: 0 green (report lines included), 1 red (a closed-without-guard entry, or a fix PR whose
guard is missing on disk), 2 when the ledger itself is unreadable (a silent clean over a corrupt
ledger is the defect rule 6d refuses).

Run: make pipeline-failure-guard-check [REPO=<owner>/<repo>] [LEDGER=…]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import bot_markers

ROOT = Path(__file__).resolve().parent.parent

LEDGER_DEFAULT = ROOT / "data" / "pipeline_failures.json"


def _repo_from_env_or_remote() -> str | None:
    """The repo to read issue state from: $GITHUB_REPOSITORY, else `git remote get-url origin`."""
    import os
    env = os.environ.get("GITHUB_REPOSITORY")
    if env:
        return env
    try:
        out = subprocess.run(["git", "remote", "get-url", "origin"], cwd=ROOT,
                             capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:
        return None
    if not out:
        return None
    # git@github.com:owner/repo.git  or  https://github.com/owner/repo(.git)
    import re
    m = re.search(r"[:/]([^/]+/[^/]+?)(?:\.git)?$", out)
    return m.group(1) if m else None


def _issue_state(repo: str, number: str) -> str | None:
    """CLOSED / OPEN, or None when INDETERMINATE (gh missing, an error, a non-list answer)."""
    try:
        proc = subprocess.run(
            ["gh", "issue", "view", str(number), "--repo", repo, "--json", "state"],
            capture_output=True, text=True, timeout=30)
        if proc.returncode != 0:
            return None
        data = json.loads(proc.stdout or "{}")
    except Exception:
        return None
    state = data.get("state")
    return state if state in ("CLOSED", "OPEN") else None


def read_ledger(path: Path) -> dict:
    if not path.exists():
        raise RuntimeError(f"ledger {path} does not exist — the filer has never run? "
                           "The gate is red on a missing ledger, not silently green.")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"ledger {path} is unreadable: {exc}") from None
    if not isinstance(data, dict) or not isinstance(data.get("failures"), list):
        raise RuntimeError(f"ledger {path} is not {{'failures': [...]}}")
    return data


def guard_test_exists(guard: str) -> bool:
    """The guard must be a module `make test` collects: a tests/test_*.py file on disk
    (the runner auto-discovers exactly that shape)."""
    if not guard:
        return False
    name = guard.split("::", 1)[0]
    path = ROOT / name
    return name.startswith("tests/test_") and name.endswith(".py") and path.is_file()


def marker_issue_states(repo: str) -> dict:
    """{run_id: {"number": n, "state": OPEN|CLOSED}} for issues carrying pipeline-run-failure.

    The ledger lives in the repo and a marker lives on the issue: if a marker issue is CLOSED and
    NO ledger entry records that run, the ledger itself is stale (its append was never landed) and
    the failure could be re-forgotten. That is a red, not a shrug. A scan that cannot run is
    indeterminate (reported, never silently green-and-empty).
    """
    try:
        proc = subprocess.run(
            ["gh", "issue", "list", "--repo", repo, "--state", "all", "--label", "tech-debt",
             "--limit", "500", "--json", "number,state,body"],
            capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            return {}
        issues = json.loads(proc.stdout)
    except Exception:
        return {}
    if not isinstance(issues, list):
        return {}
    out: dict = {}
    for issue in issues:
        for marker in bot_markers.parse_markers(issue.get("body") or ""):
            if marker["bot"] != "queued-alarm" or marker["kind"] != "failure":
                continue
            run = marker.get("run")
            if run:
                out[run] = {"number": issue.get("number"), "state": issue.get("state")}
    return out


def verdict(ledger: dict, repo: str | None, marker_states: dict | None = None) -> tuple[int, list[str]]:
    """The gate's decision over the whole ledger."""
    reports: list[str] = []
    reds: list[str] = []
    guarded = 0
    ledger_runs = {str(entry.get("run_id")) for entry in ledger["failures"]}
    # A CLOSED marker issue with no ledger entry: the diagnosis landed, the record did not.
    for run_id, info in (marker_states or {}).items():
        if info["state"] == "CLOSED" and run_id not in ledger_runs:
            reds.append(f"issue #{info['number']} (run {run_id}) is CLOSED but the ledger records "
                        "nothing for that run — append the entry and its guard (rule 3b is "
                        "append-only, so the record must land, not the memory)")
    states_by_issue = {info["number"]: info["state"] for info in (marker_states or {}).values()}
    for entry in ledger["failures"]:
        rid = entry.get("run_id")
        issue = entry.get("issue_number")
        fix_pr = entry.get("fix_pr")
        guard = entry.get("guard")
        label = f"run {rid} issue {issue or '-'}"

        if fix_pr:
            if not guard or not guard_test_exists(guard):
                reds.append(f"{label}: fix PR {fix_pr} names guard {guard or 'NOTHING'} — "
                            "no guard test is collected by `make test`, so the error class "
                            "is unguarded (reintroduction would be silent)")
            else:
                guarded += 1
            continue

        # No fix PR yet: the state of the ISSUE decides.
        if not issue:
            reports.append(f"{label}: undiagnosed filing pending a diagnosis")
            continue
        state = states_by_issue.get(issue)
        if state is None:
            state = _issue_state(repo, issue) if repo else None
        if state is None:
            reports.append(f"{label}: issue state INDETERMINATE (not counted)")
        elif state == "CLOSED":
            reds.append(f"{label}: issue CLOSED without a fix PR or a guard test — a closed "
                        "pipeline failure must carry the change and the test that keep it fixed")
        else:
            reports.append(f"{label}: open, fix in flight (reported, not red)")

    if reds:
        return 1, reds + reports
    reports.append(f"{guarded} diagnosed failure(s) closed with a landed fix PR + guard test")
    return 0, reports


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=None, help="owner/repo (default: $GITHUB_REPOSITORY/origin)")
    ap.add_argument("--ledger", default=str(LEDGER_DEFAULT))
    args = ap.parse_args(argv)
    try:
        ledger = read_ledger(Path(args.ledger))
    except RuntimeError as exc:
        print(f"pipeline-failure-guard-check: {exc}", file=sys.stderr)
        return 2
    repo = args.repo or _repo_from_env_or_remote()
    if not repo:
        print("pipeline-failure-guard-check: no repo (pass REPO= or run inside a clone)",
              file=sys.stderr)
        return 2
    states = marker_issue_states(repo)
    if not states:
        print("pipeline-failure-guard-check: note — no pipeline-run-failure markers readable "
              "(no filings yet, or the marker scan could not run)")
    rc, lines = verdict(ledger, repo, states)
    for line in lines:
        print(f"pipeline-failure-guard-check: {line}")
    if rc == 1:
        print("pipeline-failure-guard-check: RED — a diagnosed pipeline failure closed without "
              "its guard; reopen the issue or land the fix PR + guard test (issue #802)",
              file=sys.stderr)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
