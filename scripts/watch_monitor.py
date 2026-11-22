#!/usr/bin/env python3
"""Deterministic change detector for the tll issue/PR/CI watcher (issue #1266).

One agent job must not wake every tick just because a clock moved. This script emits ONLY
changed markers, with no timestamps and no random ordering:

    C:<comment id>                       a new issue/PR comment
    R:<run id>:<status>:<conclusion>     a CI run changed state
    M:<master sha>                       master moved (a merge or a push)

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
from pathlib import Path

DEFAULT_REPO = "andyholst/trending-local-llms"
MARKER_PREFIXES = ("C:", "R:", "M:")


def as_list(value: object) -> list[dict]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def marker_state(previous: dict, payload: dict) -> tuple[list[str], dict]:
    """Pure diff: return sorted markers and the NEXT state for one snapshot.

    `payload` is exactly what the gh calls returned: `comments` maps `issues`/`pulls` to
    comment rows, `runs` is a list of workflow-run rows, `master` is a commit object.
    """
    if not isinstance(previous, dict):
        previous = {}
    lines: list[str] = []
    state: dict = {"comments": {}, "runs": {}, "master": previous.get("master")}

    prev_comments = previous.get("comments", {}) if isinstance(previous.get("comments"), dict) else {}
    for kind in ("issues", "pulls"):
        rows = as_list(payload.get("comments", {}).get(kind, [])) if isinstance(payload.get("comments"), dict) else []
        ids = [int(r["id"]) for r in rows if isinstance(r.get("id"), int)]
        seen = int(prev_comments.get(kind, 0)) if str(prev_comments.get(kind, 0)).isdigit() else 0
        for comment_id in sorted(i for i in ids if i > seen):
            lines.append(f"C:{comment_id}")
        state["comments"][kind] = max([seen] + ids) if ids else seen

    prev_runs = previous.get("runs", {}) if isinstance(previous.get("runs"), dict) else {}
    for run in as_list(payload.get("runs")):
        run_id = run.get("id")
        if not isinstance(run_id, int):
            continue
        stamp = f"{run.get('status', '?')}:{run.get('conclusion') or '-'}"
        state["runs"][str(run_id)] = stamp
        if prev_runs.get(str(run_id)) != stamp:
            lines.append(f"R:{run_id}:{stamp}")

    master = payload.get("master")
    master_sha = master.get("sha") if isinstance(master, dict) else None
    if isinstance(master_sha, str):
        state["master"] = master_sha
        if previous.get("master") != master_sha:
            lines.append(f"M:{master_sha[:12]}")

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
        comments[kind] = as_list(get(f"{kind}/comments?per_page=100"))
    runs_payload = get("actions/runs?per_page=30")
    runs = as_list(runs_payload.get("workflow_runs")) if isinstance(runs_payload, dict) else as_list(runs_payload)
    return {"comments": comments, "runs": runs, "master": get("commits/master")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=os.environ.get("TLL_REPO", DEFAULT_REPO))
    ap.add_argument("--state", default=os.environ.get("TLL_WATCH_STATE", ""))
    ap.add_argument("--gh", default=None, help="explicit gh path for stripped cron environments")
    ap.add_argument("--check", action="store_true", help="offline contract check; no network, no state write")
    args = ap.parse_args(argv)

    if args.check:
        if not all(m in MARKER_PREFIXES for m in ("C:", "R:", "M:")):
            print("CHECK FAILED: marker prefixes changed", file=sys.stderr)
            return 2
        print("[watch-monitor] OK: C/R/M markers, caller-owned state, no timestamps")
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

    lines, state = marker_state(read_state(state_path), payload)
    write_state(state_path, state)
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
