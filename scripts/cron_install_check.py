#!/usr/bin/env python3
"""Verify the fleet cron installation shape on an Hermes host (issue #1270).

Reads the cron jobs.json across the Hermes homes — `$HERMES_HOME`, then
`~/.hermes`, then every `~/.hermes/profiles/*` (a named-profile host keeps
`cron/` and `scripts/` under the profile) — and refuses a host that cannot see
comments, CI runs or a merged master. It does NOT run any network call and never
reads credential VALUES — only the job shape, wrapper paths and the repo-owned
detector's marker contract.

    python3 scripts/cron_install_check.py [--jobs PATH] [--detector PATH] [--wrappers DIR]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

MARKERS = ("C:", "R:", "M:", "H:")


def load_jobs(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["jobs"] if isinstance(data, dict) else data


def hermes_homes(home: Path | None = None,
                 env_home: str | None = None) -> list[Path]:
    """Every Hermes home to search, in the order issue #1409 names.

    `$HERMES_HOME` first (a named-profile session points here), then `~/.hermes`,
    then each `~/.hermes/profiles/*` sorted by name, so the answer never depends
    on directory order. A profile home `$HERMES_HOME` already named is not
    repeated. `home=`/`env_home=` are the test seams; `env_home=None` reads
    `HERMES_HOME` from the environment.
    """
    default_home = (home or Path.home()) / ".hermes"
    raw_env = os.environ.get("HERMES_HOME") if env_home is None else env_home
    homes: list[Path] = []
    if raw_env:
        homes.append(Path(raw_env).expanduser())
    if default_home not in homes:
        homes.append(default_home)
    profiles = default_home / "profiles"
    if profiles.is_dir():
        for child in sorted(profiles.iterdir(), key=lambda p: p.name):
            if child.is_dir() and child not in homes:
                homes.append(child)
    return homes


def discover_jobs(homes: list[Path]) -> tuple[Path | None, list[dict]]:
    """The first jobs file that carries at least one job, and its jobs.

    A named-profile host can hold a profile whose `cron/jobs.json` is
    `{"jobs": []}` beside the profile that actually runs the fleet, so an EMPTY
    file is not an installation: the search continues to the next home. With no
    candidate carrying jobs the result is `(None, [])` — the caller then reports
    the existing "expected exactly 1 no-agent watchdog job" refusal instead of a
    FileNotFoundError (issue #1409: a host with no jobs fails cleanly).
    """
    empty: Path | None = None
    for home in homes:
        candidate = home / "cron" / "jobs.json"
        if not candidate.is_file():
            continue
        try:
            jobs = load_jobs(candidate)
        except (OSError, ValueError, KeyError):
            continue
        if jobs:
            return candidate, jobs
        if empty is None:
            empty = candidate
    if empty is not None:
        return empty, []
    return None, []


def problems(jobs: list[dict], detector: Path, wrappers_dir: Path) -> list[str]:
    out: list[str] = []
    watchdog = [j for j in jobs if j.get("no_agent")]
    agent = [j for j in jobs if j.get("monitor_script") or j.get("monitor")]
    if len(watchdog) != 1:
        out.append(f"expected exactly 1 no-agent watchdog job, found {len(watchdog)}")
    if len(agent) != 1:
        out.append(f"expected exactly 1 monitor-gated agent job, found {len(agent)}")
    for j in watchdog + agent:
        if not j.get("enabled", True):
            out.append(f"job {j.get('name') or j.get('job_id')} is disabled")
        if not j.get("workdir"):
            out.append(f"job {j.get('name') or j.get('job_id')} has no workdir")
    states: set[str] = set()
    for j in watchdog + agent:
        script = j.get("script") or j.get("monitor_script") or j.get("monitor") or ""
        name = j.get("name") or j.get("job_id")
        p = Path(script) if Path(script).is_absolute() else wrappers_dir / script
        if not p.exists():
            out.append(f"{name}: wrapper {p} missing")
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if "watch_monitor.py" not in text:
            out.append(f"{name}: wrapper does not call the repo-owned detector")
        if "--gh" not in text and "gh" not in text:
            out.append(f"{name}: wrapper has no explicit gh path fix")
        if j.get("monitor_script"):
            if "--heartbeat-seconds" not in text or "HEARTBEAT_SECONDS = 900" not in text:
                out.append(f"{name}: agent monitor wrapper must pass --heartbeat-seconds 900 (#1282)")
        if j.get("no_agent") and "HEARTBEAT_SECONDS = 0" not in text:
            out.append(f"{name}: no-agent watchdog must stay quiet (HEARTBEAT_SECONDS = 0, #1282)")
        for line in text.splitlines():
            if "STATE" in line and ".json" in line:
                states.add(line.strip())
    if len(states) < 2 and watchdog and agent:
        out.append("watchdog and agent must use SEPARATE state files")
    if detector.exists():
        text = detector.read_text(encoding="utf-8", errors="replace")
        for marker in MARKERS:
            if marker not in text:
                out.append(f"detector lacks marker {marker}")
    else:
        out.append(f"repo-owned detector {detector} missing")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    home = Path(os.environ.get("HERMES_HOME") or Path.home() / ".hermes")
    ap.add_argument("--jobs", default=None,
                    help="explicit jobs.json (default: discover it across the Hermes homes)")
    ap.add_argument("--detector", default="scripts/watch_monitor.py")
    ap.add_argument("--wrappers", default=None,
                    help="explicit wrappers dir (default: the matching home's scripts/)")
    args = ap.parse_args(argv)

    jobs_arg = args.jobs or os.environ.get("CRON_JOBS")
    if jobs_arg:
        jobs_path = Path(jobs_arg)
        wrappers = Path(args.wrappers) if args.wrappers else home / "scripts"
        try:
            jobs = load_jobs(jobs_path)
        except (OSError, ValueError, KeyError) as exc:
            print(f"[cron-install] FAIL cannot read cron jobs: {type(exc).__name__}")
            return 1
    else:
        jobs_path, jobs = discover_jobs(hermes_homes())
        if args.wrappers:
            wrappers = Path(args.wrappers)
        elif jobs_path is not None:
            wrappers = jobs_path.parent.parent / "scripts"
        else:
            wrappers = home / "scripts"
    bad = problems(jobs, Path(args.detector), wrappers)
    if bad:
        for b in bad:
            print(f"[cron-install] FAIL {b}")
        return 1
    print(f"[cron-install] OK {len(jobs)} job(s): watchdog + monitor-gated agent, repo-owned C/R/M detector")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
