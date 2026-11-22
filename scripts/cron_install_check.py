#!/usr/bin/env python3
"""Verify the fleet cron installation shape on an Hermes host (issue #1270).

Reads the cron jobs.json under HERMES_HOME (or ~/.hermes) and refuses a host that
cannot see comments, CI runs or a merged master. It does NOT run any network call
and never reads credential VALUES — only the job shape, wrapper paths and the
repo-owned detector's marker contract.

    python3 scripts/cron_install_check.py [--jobs PATH] [--detector PATH]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

MARKERS = ("C:", "R:", "M:")


def load_jobs(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["jobs"] if isinstance(data, dict) else data


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
    ap.add_argument("--jobs", default=os.environ.get("CRON_JOBS", str(home / "cron" / "jobs.json")))
    ap.add_argument("--detector", default="scripts/watch_monitor.py")
    ap.add_argument("--wrappers", default=str(home / "scripts"))
    args = ap.parse_args(argv)
    try:
        jobs = load_jobs(Path(args.jobs))
    except (OSError, ValueError, KeyError) as exc:
        print(f"[cron-install] FAIL cannot read cron jobs: {type(exc).__name__}")
        return 1
    bad = problems(jobs, Path(args.detector), Path(args.wrappers))
    if bad:
        for b in bad:
            print(f"[cron-install] FAIL {b}")
        return 1
    print(f"[cron-install] OK {len(jobs)} job(s): watchdog + monitor-gated agent, repo-owned C/R/M detector")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
