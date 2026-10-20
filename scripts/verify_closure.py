#!/usr/bin/env python3
"""Did the issue a merged PR claimed to close ACTUALLY close? (issue #288)

`make pr-closure` PREDICTS the closure: it reads the PR body and applies GitHub's parser
semantics (one closing keyword binds to ONE reference). It cannot prove the outcome — measured
on PR #272, where `Closes #271 and #276` closed #271 and left #276 open after the merge, and
nothing in the pipeline noticed.

So the merge job reads the MERGED PR's own `closingIssuesReferences` and fails LOUDLY when one
of them is still open. Read-only: it never merges, comments or edits.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

#: How long to let GitHub finish closing the issues a merge just closed (its own operation
#: trails the merge call by a moment). Injectable so the guard does not sleep for real.
ATTEMPTS = int(os.environ.get("VERIFY_CLOSURE_ATTEMPTS", "3"))
DELAY_S = float(os.environ.get("VERIFY_CLOSURE_DELAY_S", "2"))


def _gh(*args: str) -> dict:
    """Run `gh` and parse its JSON. A failure is LOUD — an unreadable state is never a pass."""
    proc = subprocess.run(["gh", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"[verify-closure] FAIL: gh {' '.join(args)} exited "
                         f"{proc.returncode}: {proc.stderr.strip()[:300]}")
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        raise SystemExit(f"[verify-closure] FAIL: gh {' '.join(args)} did not return JSON")


def open_references(pr: dict, repo: str | None) -> list[tuple[int, str]]:
    """Every issue the PR's body claims to close that is NOT closed, as (number, state)."""
    refs = pr.get("closingIssuesReferences") or []
    open_ones: list[tuple[int, str]] = []
    for ref in refs:
        number = ref.get("number")
        state = ref.get("state")
        if not state and number is not None:
            args = ["issue", "view", str(number), "--json", "state"]
            if repo:
                args += ["--repo", repo]
            state = _gh(*args).get("state")
        if str(state).upper() != "CLOSED":
            open_ones.append((int(number or 0), str(state or "UNKNOWN")))
    return open_ones


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify a merged PR closed what it claimed to")
    ap.add_argument("--pr", required=True, help="the merged PR number")
    ap.add_argument("--repo", default=None, help="owner/name (default: gh's own resolution)")
    args = ap.parse_args()

    base = ["pr", "view", str(args.pr), "--json", "state,closingIssuesReferences,body"]
    if args.repo:
        base += ["--repo", args.repo]
    pr = _gh(*base)
    state = str(pr.get("state") or "").upper()
    if state not in ("MERGED", "CLOSED"):
        print(f"[verify-closure] PR #{args.pr} is {state or 'UNKNOWN'} — nothing was merged yet")
        return 0

    refs = pr.get("closingIssuesReferences") or []
    if not refs:
        # A PR that closes nothing is legal (a change may reference an issue it does not
        # implement, and `make pr-closure` refuses a MISMATCH, not an absence).
        print(f"[verify-closure] OK: PR #{args.pr} claims to close no issue")
        return 0

    open_ones: list[tuple[int, str]] = []
    for attempt in range(1, ATTEMPTS + 1):
        open_ones = open_references(pr, args.repo)
        if not open_ones:
            print(f"[verify-closure] OK: PR #{args.pr} closed all {len(refs)} issue(s) it claims")
            return 0
        if attempt < ATTEMPTS:
            time.sleep(DELAY_S)

    for number, state in open_ones:
        print(f"[verify-closure] FAIL: PR #{args.pr} implements #{number} but it is {state} "
              f"after the merge — the body's closing keyword did not bind (rule 6e)",
              file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
