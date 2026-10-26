#!/usr/bin/env python3
"""A scheduled bot that is red on every run has no alarm of its own (issue #488).

`pr-health` failed on every scheduled sweep for days with a traceback nobody saw. `queued-alarm`
covers a job stuck in `queued` (#252), `sweep-alarm` covers a sweep that was never delivered (#497),
`pr-health` covers a PR whose checks never ran (#475) — but **nothing read "this bot's own cron is
failing"**, and the failing step was the one whose job is to make silence loud, so its silence
removed its own alarm. Every bot here is a cron expected to be green: a red one is indistinguishable
in the product from a quiet one, and the longer it stays red the more of its guard rails silently
stop existing.

This is the pipeline-level alarm: it lists each CRON pipeline of this repository (derived from the
workflows themselves, never hand-maintained) and fails when a pipeline's last N scheduled runs all
concluded in failure, naming the newest run URL.

Read-only: it never comments, never dispatches, never writes a file.

Usage:
    python3 scripts/bot_health.py [--root .] [--repo OWNER/NAME] [--limit 3] [--list]

Exit: 0 = every cron pipeline has a green scheduled run in its window; 1 = at least one has N
consecutive failures (the URL is printed); 2 = the pipeline list is empty or `gh` could not answer
(refusing to report a clean bill of health it did not measure).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

WORKFLOWS = Path(".github/workflows")

#: A conclusion that means "this run did not do its job".
BAD = frozenset({"failure", "timed_out", "cancelled", "startup_failure"})

#: A workflow's `schedule:` trigger, in any of the shapes GitHub accepts.
#: A `- cron: …` line, with an OPTIONAL trailing comment — every workflow here annotates its cron
#: ("# four times a day, off the hour"), and a regex that ignores the comment silently drops those
#: pipelines from the alarm (measured on this very file: it listed four of eight).
_CRON = re.compile(r"^\s*-\s*cron:\s*['\"]?[^'\"\n]+['\"]?\s*(?:#.*)?$", re.M)


def cron_pipelines(root: Path) -> list[str]:
    """Every workflow in `root` that runs on a cron, as its file name.

    Derived from the tree: a workflow added tomorrow is covered without editing this module. This
    module's own pipeline is included on purpose — an alarm that stops running is exactly the
    failure it exists to catch, and its own last runs are the evidence.
    """
    out: list[str] = []
    for path in sorted((root / WORKFLOWS).glob("*.yml")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if _CRON.search(text):
            out.append(path.name)
    return out


def gh(args: list[str]) -> str:
    proc = subprocess.run(["gh", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"[bot-health] gh {' '.join(args)} failed: "
                         f"{(proc.stderr or proc.stdout).strip()[:400]}")
    return proc.stdout


def scheduled_runs(repo: str, workflow: str, limit: int) -> list[dict]:
    """The newest `limit` SCHEDULE deliveries of `workflow` (a manual run proves nothing)."""
    out = gh(["run", "list", "--repo", repo, "--workflow", workflow, "--event", "schedule",
              "--limit", str(limit), "--json", "conclusion,databaseId,url,createdAt"])
    try:
        return json.loads(out or "[]")
    except json.JSONDecodeError:
        raise SystemExit(f"[bot-health] gh returned non-JSON for {workflow}: {out[:200]}")


def verdict(runs: list[dict], limit: int) -> tuple[bool, str]:
    """(is_failing, why) for one pipeline, from its newest scheduled runs.

    A window SHORTER than `limit` is not a failure: a pipeline that was added yesterday has not had
    three chances yet, and calling that red would make the alarm cry wolf on every new bot.
    """
    if not runs:
        return False, "no scheduled run yet"
    if len(runs) < limit:
        return False, f"only {len(runs)} scheduled run(s) so far"
    bad = [r for r in runs[:limit] if str(r.get("conclusion") or "").lower() in BAD]
    if len(bad) < limit:
        return False, f"{len(bad)}/{limit} of the newest runs failed"
    newest = runs[0]
    return True, (f"the last {limit} scheduled runs ALL failed (newest "
                  f"{newest.get('conclusion')}: {newest.get('url')})")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fail when a cron pipeline's own runs are all red "
                                            "(issue #488)")
    ap.add_argument("--root", default=".")
    ap.add_argument("--repo", default="", help="OWNER/NAME (default: as gh reports it)")
    ap.add_argument("--limit", type=int, default=3, help="how many newest scheduled runs to read")
    ap.add_argument("--list", action="store_true", help="print the pipelines and exit")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    pipelines = cron_pipelines(root)
    if not pipelines:
        print(f"[bot-health] FAIL: no cron pipeline found under {root / WORKFLOWS} — the alarm "
              f"would measure nothing", file=sys.stderr)
        return 2
    if args.list:
        print("\n".join(pipelines))
        return 0
    if args.limit < 1:
        print("[bot-health] FAIL: --limit 0 checks nothing", file=sys.stderr)
        return 2

    repo = args.repo or gh(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"]).strip()
    if not repo:
        print("[bot-health] FAIL: no repository to read runs from", file=sys.stderr)
        return 2

    failing: list[str] = []
    for workflow in pipelines:
        runs = scheduled_runs(repo, workflow, args.limit)
        bad, why = verdict(runs, args.limit)
        print(f"[bot-health] {'FAIL' if bad else 'ok  '} {workflow}: {why}")
        if bad:
            failing.append(f"{workflow} — {why}")

    if failing:
        print(f"\n[bot-health] {len(failing)} cron pipeline(s) are red on every scheduled run:",
              file=sys.stderr)
        for line in failing:
            print(f"[bot-health]   - {line}", file=sys.stderr)
        return 1
    print(f"[bot-health] OK: {len(pipelines)} cron pipeline(s) each have a green scheduled run "
          f"in the last {args.limit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
