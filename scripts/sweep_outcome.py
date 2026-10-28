#!/usr/bin/env python3
"""The sweep's own outcome comment when a run dies before its verdict.

`issue-bot.yml`'s `implement` job speaks on the issue it picked only from a step that OWNS a
comment: `Apply the implementer's verdict` (for `refine` / `close`) and `Report the outcome on
the issue` (for `implement`, gated on the verdict's value). So a run that STARTS and then dies
before its verdict — a resolver that could not read the issue, a checkout or base assertion that
refused, an image or smoke step that failed, an agent that wrote no `triage.md` so
`make issue-verdict` exits 2 — posted the start marker and then NOTHING. The issue kept showing
"an implementer has started" for ever, the red job lived only in the Actions tab (#488), and
since #496 the sweep drains 48 open issues one per delivery: one dead run is a day of queue with
no artifact on the queue item itself.

The delivery half is already loud (`scripts/sweep_alarm.py`, #498). This is the ARTIFACT half: one
comment, on the issue the sweep picked, saying the run stopped and where.

The decision is PURE (`owed()`), so it is testable without a network and without a workflow:

    implemented?  closed in flight?  verdict        -> owe a comment?
    false         -                  -              -> no (nothing was picked/implemented)
    true          true               -              -> no (the already-fixed notice owns it)
    true          false              implement      -> no (the outcome comment owns it)
    true          false              refine/close   -> no (the verdict step commented)
    true          false              (none)         -> YES — the run died before its verdict

`--post` writes through `gh issue comment` (default `github.token`; the owner PAT cannot comment,
measured on #124) ONCE PER RUN: a re-run of the same run id finds its own marker and says nothing,
while a comment from an EARLIER run never suppresses this one. The body arrives on stdin
(`--body-file -`), so no scratch file exists for a later `git add -A` to commit.

Exit codes: 0 = posted, or nothing was owed/already said; 2 = refused or unreadable (no issue, a
non-numeric issue, `gh` failing) — a tool that cannot read a run's state must never report a pass.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bot_markers as bm  # noqa: E402  (the ONE definition of the marker's name and shape)

#: The verdicts whose own step already posts a comment — this tool must not add a second one.
OWN_OUTCOME = ("implement", "refine", "close")


class GhError(RuntimeError):
    """A `gh` call that failed — reported loudly, and NEVER as a clean result."""


def _gh(args: list[str], stdin: str | None = None) -> str:
    """Run `gh`; a failure RAISES (a read we cannot make is never a clean result)."""
    proc = subprocess.run(["gh", *args], input=stdin, capture_output=True, text=True)
    if proc.returncode != 0:
        raise GhError(f"gh {' '.join(args[:3])} failed: {proc.stderr.strip()}")
    return proc.stdout


def owed(*, implement: bool, closed: bool, verdict: str) -> tuple[bool, str]:
    """Does this run owe an outcome comment? (decision, why) — pure, so it is testable.

    The refusal always NAMES its reason: a silent skip and a skip for the wrong reason look the
    same in a log, and the second one is how the gap this closes stayed invisible.
    """
    if not implement:
        return False, "this run resolved no open issue, so there is nothing to comment on"
    if closed:
        return False, "the issue was closed while the run was in flight - the already-fixed notice owns it"
    if verdict in OWN_OUTCOME:
        return False, f"the run reached its verdict ('{verdict}') - that step commented already"
    if verdict:
        return False, f"the run reported an unexpected verdict ('{verdict}') - left to a human"
    return True, "the run stopped before its verdict, so nothing else spoke for it"


def comment_body(*, issue: str, marker: str, run_url: str, branch: str,
                 stages: dict[str, str]) -> str:
    """The one comment a dead sweep posts: what ran, where it stopped, and that it stopped."""
    stage_line = " · ".join(f"{name}={value or 'not reached'}" for name, value in stages.items())
    lines = [
        marker,
        "",
        "**The sweep stopped before it could report an outcome on this issue.**",
        "",
        f"- issue: #{issue}",
        f"- branch: `{branch or 'none resolved'}`",
        f"- run: {run_url or 'not recorded'}",
        f"- stages: {stage_line}",
        "",
        "The run is red in the Actions tab, and the delivery alarm (`make sweep-alarm`) reports the",
        "failed delivery on its next pass. Nothing was committed, pushed or opened by this run: it",
        "stopped before the steps that do that. The next sweep picks this issue up again unless a",
        "branch or PR from an earlier run now implements it.",
    ]
    return "\n".join(lines) + "\n"


def already_said(comments: list[dict], run_id: str) -> str | None:
    """Which earlier comment already speaks for THIS run id — or None.

    Two owners are recognised: this tool's own marker (with `run=<id>`), and the
    `issue-bot-already-fixed` notice, whose stamp IS the run id (`: <run id> -->`, not a
    timestamp), so that a run which found its issue closed in flight is not commented twice.
    """
    if not run_id:
        return None      # nothing to dedup on: a hand-run carries no run id
    for comment in comments:
        body = comment.get("body") or ""
        if bm.read_marker(body, "issue-bot", "outcome") and f"run={run_id}" in body:
            return "outcome"
        if f"<!-- {bm.marker_name('issue-bot', 'already_fixed')}: {run_id} -->" in body:
            return "already-fixed"
    return None


def _comments(repo: str, issue: str) -> list[dict]:
    out = _gh(["api", f"repos/{repo}/issues/{issue}/comments?per_page=100",
               "--jq", "[.[] | {createdAt, body}]"])
    try:
        return json.loads(out or "[]")
    except json.JSONDecodeError as exc:
        raise GhError(f"could not read #{issue}'s comments: {exc}") from None


def _stages(values: list[str]) -> dict[str, str]:
    """`name=outcome` pairs, in the order the workflow passed them (its step order)."""
    out: dict[str, str] = {}
    for value in values:
        name, _, outcome = value.partition("=")
        if name.strip():
            out[name.strip()] = outcome.strip()
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Say on the picked issue that the sweep died before its verdict (the second "
                    "half of #498)")
    ap.add_argument("--repo", default=os.environ.get("REPO") or os.environ.get("GITHUB_REPOSITORY"))
    ap.add_argument("--issue", default=os.environ.get("ISSUE"))
    ap.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID"))
    ap.add_argument("--run-url", default=os.environ.get("RUN_URL"))
    ap.add_argument("--branch", default=os.environ.get("BRANCH") or "")
    ap.add_argument("--stage", action="append", default=[], metavar="NAME=OUTCOME",
                    help="a step and its GitHub outcome, in order (repeatable)")
    ap.add_argument("--stages", default=os.environ.get("STAGES") or "",
                    help="the same as `--stage`, whitespace-separated (what `make` passes)")
    ap.add_argument("--verdict", default=os.environ.get("VERDICT") or "",
                    help="the verdict the run reached (empty = it died before one)")
    ap.add_argument("--closed", action="store_true",
                    help="the issue was found closed while the run was in flight")
    ap.add_argument("--no-implement", action="store_true",
                    help="the run resolved no open issue (nothing to comment on)")
    ap.add_argument("--now", default=None, help="Iso8601 instant for the marker (tests)")
    ap.add_argument("--post", action="store_true", help="write the comment (default: print it)")
    args = ap.parse_args(argv)

    issue = (args.issue or "").strip()
    if not issue:
        print("[issue-outcome] FAIL: no issue to report on (--issue / ISSUE)", file=sys.stderr)
        return 2
    if not issue.lstrip("#").isdigit():
        print(f"[issue-outcome] FAIL: '{issue}' is not an issue number", file=sys.stderr)
        return 2
    issue = issue.lstrip("#")

    decision, why = owed(implement=not args.no_implement, closed=args.closed, verdict=args.verdict)
    if not decision:
        print(f"[issue-outcome] nothing owed for #{issue}: {why}")
        return 0

    now = dt.datetime.now(dt.timezone.utc)
    if args.now:
        try:
            now = dt.datetime.fromisoformat(args.now.replace("Z", "+00:00"))
        except ValueError:
            print(f"[issue-outcome] FAIL: --now is not an ISO8601 instant: '{args.now}'",
                  file=sys.stderr)
            return 2
    marker = bm.start_marker("issue-bot", now, args.run_id, kind="outcome")
    body = comment_body(issue=issue, marker=marker, run_url=args.run_url or "",
                        branch=args.branch,
                        stages=_stages(args.stage + args.stages.split()) or {"sweep": "unknown"})

    if not args.post:
        print(f"[issue-outcome] would comment on #{issue}: {why}")
        print(body, end="")
        return 0

    if not args.repo:
        print("[issue-outcome] FAIL: no --repo / REPO / GITHUB_REPOSITORY to read comments from",
              file=sys.stderr)
        return 2
    try:
        said = already_said(_comments(args.repo, issue), args.run_id or "")
        if said:
            print(f"[issue-outcome] #{issue} already carries this run's {said} comment - "
                  f"no duplicate (run={args.run_id})")
            return 0
        # The body arrives on stdin: no scratch file for a later `git add -A` to commit.
        _gh(["issue", "comment", issue, "--repo", args.repo, "--body-file", "-"], stdin=body)
    except GhError as exc:
        print(f"[issue-outcome] FAIL: {exc}", file=sys.stderr)
        return 2
    print(f"[issue-outcome] commented the outcome on #{issue} (run={args.run_id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
