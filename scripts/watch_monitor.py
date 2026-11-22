#!/usr/bin/env python3
"""Deterministic change detector for the tll issue/PR/CI watcher (issue #1266).

One agent job must not wake every tick just because a clock moved. This script emits ONLY
changed markers, with no timestamps and no random ordering:

    C:<comment id>                       a new issue/PR comment
    R:<run id>:<status>:<conclusion>[:<workflow>]  a CI run changed state
    M:<master sha>                       master moved (a merge or a push)
    H:<bucket>                           opt-in work heartbeat (--heartbeat-seconds N)

With no heartbeat flag the quiet tick is still silent. The heartbeat is a bucket of
wall-clock time divided by N, never a timestamp, so identical ticks look identical to
the caller's state file and only the bucket boundary wakes the agent.

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

DEFAULT_REPO = "andyholst/trending-local-llms"
MARKER_PREFIXES = ("C:", "R:", "M:", "H:")

# The minimum settle window between a wake-up and a claim, in seconds (issue #1312).
#
# The watcher is deliberately timestamp-free, so it cannot filter a marker by age; the
# window is the floor the WOKEN lane applies before it claims, and this constant is the
# ONE place the number lives — `AGENTS.md` §7b names it and `make watch-monitor --check`
# refuses a weaker floor, so neither the rulebook row nor the pin can be dropped silently.
CLAIM_SETTLE_SECONDS = 180
CLAIM_SETTLE_FLOOR_SECONDS = 60


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
        token = workflow_token(run.get("name"))
        if token:
            stamp += f":{token}"
        state["runs"][str(run_id)] = stamp
        if prev_runs.get(str(run_id)) != stamp:
            lines.append(f"R:{run_id}:{stamp}")

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
    ap.add_argument("--claim-settle-seconds", type=int, default=CLAIM_SETTLE_SECONDS,
                    dest="claim_settle_seconds",
                    help="the settle window a caller applies before claiming "
                         f"(default {CLAIM_SETTLE_SECONDS}s, floor {CLAIM_SETTLE_FLOOR_SECONDS}s)")
    ap.add_argument("--heartbeat-seconds", type=int, default=0,
                    dest="heartbeat_seconds",
                    help="opt-in deterministic H marker every N seconds (0 disables)")
    args = ap.parse_args(argv)

    if args.check:
        if not all(m in MARKER_PREFIXES for m in ("C:", "R:", "M:", "H:")):
            print("CHECK FAILED: marker prefixes changed", file=sys.stderr)
            return 2
        if args.claim_settle_seconds < CLAIM_SETTLE_FLOOR_SECONDS:
            print(f"CHECK FAILED: the claim settle window {args.claim_settle_seconds}s is below "
                  f"the {CLAIM_SETTLE_FLOOR_SECONDS}s floor", file=sys.stderr)
            return 2
        print(f"[watch-monitor] OK: C/R/M/H markers, caller-owned state, no timestamps; "
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
