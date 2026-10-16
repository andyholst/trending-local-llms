#!/usr/bin/env python3
"""The refresh run's WINDOW as a machine-readable block (issue #199).

An in-flight refresh is invisible: the four searches run in parallel for ~12 minutes and only
THEN does `aggregate` open a PR (and only when there is new data). Until that PR exists nothing a
reader can open says a refresh is running, and the PR it opens carried no timestamps at all — so
"which run wrote this, and when did each leg start?" was answerable only from the Actions API,
which a reviewer reading the PR page cannot see. A verdict taken against `master` while a refresh
is in flight can be invalidated by that PR landing minutes later (#177 is the overlap half; this
is the readable-window half).

The block is composed from the run's REAL job timestamps read from the GitHub API — never from a
wall clock at PR-open time — and its marker line is written by the SHARED helper (#197,
`scripts/bot_markers.py`), so `scripts/issue_queue.py` or any future reader parses it like every
other bot marker.

    <!-- refresh-bot-run: <ISO8601Z> run=<id> -->
    started=<ISO8601Z> · legs: nvidia=<ISO8601Z> metal=<ISO8601Z> cpu=<ISO8601Z> amd=<ISO8601Z> · aggregate=<ISO8601Z>
    run: <run URL>

Two surfaces embed it: the PR body `aggregate` opens, and the data-gap issue `make data-gap-issue`
files — an issue filed BY a refresh can then be told apart from one filed by an earlier run.

Usage:
    make refresh-run-block                 # the current run, from the API
    python3 scripts/refresh_run_block.py render --jobs-json fixture.json   # tests / offline
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bot_markers as bm  # noqa: E402  (ONE definition of the marker name/shape)

#: The four search legs, in the canonical order the repo renders them (AGENTS.md §6b).
LEGS = ("nvidia", "metal", "cpu", "amd")

#: A matrix job's rendered name, e.g. `search (nvidia)`.
_LEG_JOB = re.compile(r"^search \((?P<backend>[a-z]+)\)$")


def _iso(stamp: str | None) -> str:
    """A GitHub `started_at` (or a fixture's) as the `<ISO8601Z>` the block prints."""
    if not stamp:
        return "unknown"
    # GitHub sends `2026-10-15T20:32:13Z`; accept an offset form too and normalise to Z.
    try:
        parsed = dt.datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except ValueError:
        return str(stamp)
    return parsed.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def legs_and_aggregate(jobs: list[dict]) -> tuple[dict[str, str], str | None, str | None]:
    """(per-leg started_at, aggregate started_at, the run's own run_started_at) from the job list.

    Reads the REAL job names the API returns (`search (nvidia)`, `aggregate`) — the matrix's
    rendered names, so a new backend is picked up by its name and not by a hardcoded index.
    """
    legs: dict[str, str] = {}
    aggregate: str | None = None
    for job in jobs or []:
        name = str(job.get("name", ""))
        started = job.get("started_at")
        m = _LEG_JOB.match(name)
        if m and m.group("backend") in LEGS:
            legs[m.group("backend")] = _iso(started)
        elif name == "aggregate":
            aggregate = _iso(started)
    return legs, aggregate, None


def render(run_started: str | None, legs: dict[str, str], aggregate: str | None,
           run_id: str | int, run_url: str) -> str:
    """The block as text — pure, so a fixed fixture renders exactly the expected string."""
    when = dt.datetime.fromisoformat(str(run_started).replace("Z", "+00:00"))
    # The marker line comes from the SHARED writer, so the shape can never drift from the parser.
    marker = bm.start_marker("refresh-bot", when, run_id, kind="run")
    leg_text = " ".join(f"{name}={legs.get(name, 'unknown')}" for name in LEGS)
    return "\n".join([
        marker,
        f"started={_iso(run_started)} · legs: {leg_text} · aggregate={aggregate or 'unknown'}",
        f"run: {run_url}",
    ])


def _gh_json(args: list[str]) -> dict:
    """One `gh api` read. Fails LOUDLY: a window we cannot read must never read as a clean run."""
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"[refresh-run-block] gh {' '.join(args)} failed: {out.stderr.strip()}")
    return json.loads(out.stdout or "{}")


def fetch(repo: str, run: str) -> tuple[str | None, dict[str, str], str | None, str, str]:
    """Read the run + its jobs from the API and return (started, legs, aggregate, id, url)."""
    meta = _gh_json([f"repos/{repo}/actions/runs/{run}"])
    jobs = _gh_json([f"repos/{repo}/actions/runs/{run}/jobs?per_page=100"]).get("jobs", [])
    legs, aggregate, _ = legs_and_aggregate(jobs)
    url = str(meta.get("html_url") or f"https://github.com/{repo}/actions/runs/{run}")
    return meta.get("run_started_at"), legs, aggregate, str(run), url


def current_block(repo: str | None = None, run: str | None = None) -> str:
    """The block for the run we are IN, or "" when there is no run to describe.

    "" is for a hand run (`make data-gap-issue` on a laptop has no run id) — never for a failure:
    a `gh` read that fails raises out of `fetch`, because a window we cannot read must not read
    as a clean run (#199).
    """
    repo = repo or os.environ.get("GITHUB_REPOSITORY", "")
    run = run or os.environ.get("GITHUB_RUN_ID", "")
    if not repo or not run:
        return ""
    started, legs, aggregate, run_id, url = fetch(repo, run)
    return render(started, legs, aggregate, run_id, url)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="The refresh run's window block (issue #199).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render", help="print the block for a run (the current one by default)")
    r.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    r.add_argument("--run", default=os.environ.get("GITHUB_RUN_ID", ""))
    # A RECORDED fixture the real client reads — the permitted external stand-in (rule 6m): the
    # render path below still runs the production code, it just does not hit the network.
    r.add_argument("--jobs-json", default="", help="a jobs fixture instead of the live API")
    args = ap.parse_args(argv)

    if args.jobs_json:
        payload = json.loads(Path(args.jobs_json).read_text(encoding="utf-8"))
        legs, aggregate, _ = legs_and_aggregate(payload.get("jobs", []))
        started = payload.get("run_started_at")
        run_id = str(payload.get("run_id") or args.run or "0")
        url = str(payload.get("html_url") or f"https://github.com/{args.repo}/actions/runs/{run_id}")
    else:
        if not args.repo or not args.run:
            raise SystemExit("[refresh-run-block] GITHUB_REPOSITORY/GITHUB_RUN_ID unset "
                             "(or pass --repo/--run); refusing to print a block with no run")
        started, legs, aggregate, run_id, url = fetch(args.repo, args.run)

    print(render(started, legs, aggregate, run_id, url))
    return 0


if __name__ == "__main__":
    sys.exit(main())
