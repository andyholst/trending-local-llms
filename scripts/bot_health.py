#!/usr/bin/env python3
"""A scheduled bot that is red on every run has no alarm of its own (issue #488).

`pr-health` failed on every scheduled sweep for days with a traceback nobody saw. `queued-alarm`
covers a job stuck in `queued` (#252), `sweep-alarm` covers a sweep that was never delivered (#497),
`pr-health` covers a PR whose checks never ran (#475) — but **nothing read "this bot's own cron is
failing"**, and the failing step was the one whose job is to make silence loud, so its silence
removed its own alarm. Every bot here is a cron expected to be green: a red one is indistinguishable
in the product from a quiet one, and the longer it stays red the more of its guard rails silently
stop existing.

This is the pipeline-level alarm: it lists each pipeline whose own runs nobody else reads — a CRON
pipeline (issue #488) AND a DISPATCH-ONLY pipeline (issue #1186) — derived from the workflows
themselves, never hand-maintained, and fails when a pipeline's last N deliveries all concluded in
failure, naming the newest run URL. Cron pipelines are read by `schedule`; a dispatch-only pipeline
has no schedule, so its `workflow_dispatch` runs are its only delivery and the evidence this alarm
reads. After issue #1029 only refresh-bot keeps a cron, so a cron-only read made this alarm's own
repeated failures invisible.

Read-only: it never comments, never dispatches, never writes a file.

Usage:
    python3 scripts/bot_health.py [--root .] [--repo OWNER/NAME] [--limit 3] [--list]

Exit: 0 = every watched pipeline has a green run in its window; 1 = at least one has N consecutive
failures (the URL is printed); 2 = the pipeline list is empty or `gh` could not answer (refusing to
report a clean bill of health it did not measure).
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

#: A workflow whose ONLY trigger is `workflow_dispatch` (issue #1186). Its dispatched runs are
#: its only delivery — after #1029 it has no cron, so a cron-only reader cannot see it fail.
_DISPATCH = re.compile(r"^\s*workflow_dispatch:\s*(?:#.*)?$", re.M)
_ON_KEY = re.compile(r"^on:\s*(?:#.*)?$")
_EVENT_KEY = re.compile(r"^\s{2}([A-Za-z_][\w-]*):")


def workflow_triggers(text: str) -> set[str]:
    """Event names under a workflow's top-level `on:` block (issue #1186).

    A line-oriented read keeps this read-only alarm free of a PyYAML dependency: event keys are
    two spaces in, the block ends at the next column-zero key, and nested `cron:`/`inputs:` lines
    and comments are ignored. A workflow with any event besides `workflow_dispatch` is exercised
    by that event (issue #231) and is not dispatch-only.
    """
    out: set[str] = set()
    in_on = False
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if not in_on:
            if _ON_KEY.match(line):
                in_on = True
            continue
        if indent == 0:
            break
        if indent == 2:
            m = _EVENT_KEY.match(line)
            if m:
                out.add(m.group(1))
    return out


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


def watched_pipelines(root: Path) -> list[str]:
    """Every pipeline whose own failures nobody else reads (issue #1186).

    The cron set (issue #488) is kept, and a DISPATCH-ONLY pipeline joins it: a pipeline whose only
    trigger is `workflow_dispatch` is exercised by no PR (issue #231) and, after #1029, has no
    schedule — so a cron-only reader cannot see its own red runs. A pipeline with a push/PR trigger
    is left out: a change exercises it directly, and a collaborator's manual dispatch of it is that
    person's own act (the #1029 partition).
    """
    out = set(cron_pipelines(root))
    for path in sorted((root / WORKFLOWS).glob("*.yml")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if _DISPATCH.search(text) and workflow_triggers(text) == {"workflow_dispatch"}:
            out.add(path.name)
    return sorted(out)


def gh(args: list[str]) -> str:
    proc = subprocess.run(["gh", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"[bot-health] gh {' '.join(args)} failed: "
                         f"{(proc.stderr or proc.stdout).strip()[:400]}")
    return proc.stdout


def pipeline_runs(repo: str, workflow: str, limit: int, event: str) -> list[dict]:
    """The newest `limit` deliveries of `workflow` for `event` — schedule OR workflow_dispatch.

    A manual dispatch of a cron/push pipeline proves nothing; a dispatched run of a DISPATCH-ONLY
    pipeline is its only delivery and is the evidence this alarm reads (issue #1186).
    """
    out = gh(["run", "list", "--repo", repo, "--workflow", workflow, "--event", event,
              "--limit", str(limit), "--json", "conclusion,databaseId,url,createdAt"])
    try:
        return json.loads(out or "[]")
    except json.JSONDecodeError:
        raise SystemExit(f"[bot-health] gh returned non-JSON for {workflow}: {out[:200]}")


def scheduled_runs(repo: str, workflow: str, limit: int) -> list[dict]:
    """The cron pipeline's scheduled deliveries (the pre-#1186 name, kept additive)."""
    return pipeline_runs(repo, workflow, limit, "schedule")


def verdict(runs: list[dict], limit: int, event: str = "schedule") -> tuple[bool, str]:
    """(is_failing, why) for one pipeline, from its newest runs for its own trigger.

    A window SHORTER than `limit` is not a failure: a pipeline that was added yesterday has not had
    three chances yet, and calling that red would make the alarm cry wolf on every new bot.
    """
    kind = "scheduled" if event == "schedule" else "dispatched"
    if not runs:
        return False, f"no {kind} run yet"
    if len(runs) < limit:
        return False, f"only {len(runs)} {kind} run(s) so far"
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
    pipelines = watched_pipelines(root)
    if not pipelines:
        print(f"[bot-health] FAIL: no watched pipeline found under {root / WORKFLOWS} — the alarm "
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

    cron = set(cron_pipelines(root))
    failing: list[str] = []
    for workflow in pipelines:
        event = "schedule" if workflow in cron else "workflow_dispatch"
        runs = pipeline_runs(repo, workflow, args.limit, event)
        bad, why = verdict(runs, args.limit, event)
        print(f"[bot-health] {'FAIL' if bad else 'ok  '} {workflow} ({event}): {why}")
        if bad:
            failing.append(f"{workflow} — {why}")

    if failing:
        print(f"\n[bot-health] {len(failing)} watched pipeline(s) are red on every run:",
              file=sys.stderr)
        for line in failing:
            print(f"[bot-health]   - {line}", file=sys.stderr)
        return 1
    print(f"[bot-health] OK: {len(pipelines)} watched pipeline(s) each have a green run in the "
          f"last {args.limit} deliveries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
